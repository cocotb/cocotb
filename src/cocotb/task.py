# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import collections.abc
import inspect
import logging
import traceback
from asyncio import CancelledError, InvalidStateError
from enum import auto
from types import CoroutineType
from typing import (
    Any,
    Callable,
    Coroutine,
    Generator,
    Generic,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
    cast,
)

import cocotb
import cocotb._scheduler
import cocotb.triggers
from cocotb._deprecation import deprecated
from cocotb._outcomes import Error, Outcome, Value
from cocotb._py_compat import cached_property
from cocotb._utils import DocEnum, extract_coro_stack, remove_traceback_frames

#: Task result type
ResultType = TypeVar("ResultType")


class TaskState(DocEnum):
    """State of a Task."""

    UNSTARTED = (auto(), "Task created, but never run and not scheduled")
    SCHEDULED = (auto(), "Task in Scheduler queue to run soon")
    PENDING = (auto(), "Task waiting for Trigger to fire")
    RUNNING = (auto(), "Task is currently running")
    FINISHED = (auto(), "Task has finished with a value or Exception")
    CANCELLED = (auto(), "Task was cancelled before it finished")


class Task(Generic[ResultType]):
    """Concurrently executing task.

    This class is not intended for users to directly instantiate.
    Use :func:`cocotb.create_task` to create a Task object,
    or use :func:`cocotb.start_soon` or :func:`cocotb.start` to
    create a Task and schedule it to run.

    .. versionchanged:: 1.8.0
        Moved to the ``cocotb.task`` module.

    .. versionchanged:: 2.0
        The ``retval``, ``_finished``, and ``__bool__`` methods were removed.
        Use :meth:`result`, :meth:`done`, and :meth:`done` methods instead, respectively.
    """

    _id_count = 0  # used by the scheduler for debug

    def __init__(self, inst: Coroutine[cocotb.triggers.Trigger, None, Any]) -> None:
        self._native_coroutine = False
        if inspect.iscoroutinefunction(inst):
            raise TypeError(
                f"Coroutine function {inst} should be called prior to being "
                "scheduled."
            )
        elif inspect.isasyncgen(inst):
            raise TypeError(
                f"{inst.__qualname__} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await."
            )
        elif inspect.iscoroutine(inst):
            self._native_coroutine = True
        elif not isinstance(inst, collections.abc.Coroutine):
            raise TypeError(f"{inst} isn't a valid coroutine!")

        self._coro: Coroutine[cocotb.triggers.Trigger, None, Any] = inst
        self._state: TaskState = TaskState.UNSTARTED
        self._result: Union[Outcome[ResultType], None] = None
        self._callback_handle: Union[
            cocotb.triggers._CallbackHandle, cocotb._scheduler.CallbackHandle, None
        ] = None
        self._resume_value: Outcome[Any] = Value(None)
        self._done_callbacks: List[Callable[[Task[Any]], Any]] = []

        self._task_id = self._id_count
        type(self)._id_count += 1
        _all_tasks.add(self)

        self.name = f"Task {self._task_id}"

    @cached_property
    def log(self) -> logging.Logger:
        # Creating a logger is expensive, only do it if we actually plan to
        # log anything
        return logging.getLogger(f"cocotb.{self.name}.{self._coro.__qualname__}")

    def _get_coro_stack(self) -> traceback.StackSummary:
        """Get the coroutine callstack of this Task."""

        if not self._native_coroutine:
            raise TypeError(
                f"Can't get stack of object of type {type(self._coro).__qualname__}"
            )

        coro_stack = extract_coro_stack(cast(CoroutineType, self._coro))

        # Remove Trigger.__await__() from the stack, as it's not really useful
        if len(coro_stack) > 0 and coro_stack[-1].name == "__await__":
            coro_stack.pop()

        return coro_stack

    def __repr__(self) -> str:
        if self._native_coroutine:
            coro_stack = self._get_coro_stack()
            try:
                coro_name = coro_stack[-1].name
            # coro_stack may be empty if:
            # - exhausted generator
            # - finished coroutine
            except IndexError:
                try:
                    coro_name = self._coro.__name__
                except AttributeError:
                    coro_name = type(self._coro).__name__
        else:
            # TODO is repr appropriate here?
            coro_name = repr(self._coro)

        if self._state is TaskState.RUNNING:
            fmt = "<{name} running coro={coro}()>"
        elif self._state is TaskState.FINISHED:
            fmt = "<{name} finished coro={coro}() outcome={outcome}>"
        elif self._state is TaskState.PENDING:
            fmt = "<{name} pending coro={coro}() trigger={trigger}>"
        elif self._state is TaskState.SCHEDULED:
            fmt = "<{name} scheduled coro={coro}()>"
        elif self._state is TaskState.UNSTARTED:
            fmt = "<{name} created coro={coro}()>"
        elif self._state is TaskState.CANCELLED:
            fmt = (
                "<{name} cancelled coro={coro} with={cancelled_error} outcome={outcome}"
            )
        else:
            raise RuntimeError("Task in unknown state")

        # TODO fix this
        repr_string = fmt.format(
            name=self.name,
            coro=coro_name,
            trigger=self._trigger,
            outcome=self._result,
            cancelled_error=self._cancelled_error,
        )
        return repr_string

    def _schedule_resume(self) -> None:
        """Schedule the Task to resume execution."""
        self._callback_handle = cocotb._scheduler.instance.schedule(self._resume)
        self._state = TaskState.SCHEDULED

    def _resume(self) -> None:
        """Resume execution of the Task.

        Runs until the coroutine ends, raises, or yields a Trigger.

        Args:
            outcome: The :any:`outcomes.Outcome` object to resume with.

        Returns:
            The object yielded from the coroutine or None if coroutine finished
        """
        self._state = TaskState.RUNNING
        global _current_task
        _current_task = self

        # Run coroutine with the resume value
        try:
            trigger = self._resume_value.send(self._coro)
        except StopIteration as e:
            self._result = Value(e.value)
            self._state = TaskState.FINISHED
            return self._cleanup()
        except BaseException as e:
            self._result = Error(remove_traceback_frames(e, ["_resume", "send"]))
            self._state = TaskState.FINISHED
            return self._cleanup()
        finally:
            _current_task = None

        # Check we have a Trigger and provide a more informative error message if not
        if not isinstance(trigger, cocotb.triggers.Trigger):
            self._resume_value = Error(
                TypeError(
                    f"cocotb scheduler can only handle Triggers, got {type(trigger).__qualname__}"
                )
            )
            return self._schedule_resume()

        # Try to register the Task to resume when the Trigger fires
        try:
            self._callback_handle = trigger._register(self._schedule_resume)
        except Exception as e:
            remove_traceback_frames(e, ["_resume"])
            self._resume_value = Error(e)
            return self._schedule_resume()
        else:
            self._state = TaskState.PENDING

    def _cleanup(self) -> None:
        # Close coroutine so there is no RuntimeWarning that it was never awaited
        self._coro.close()

        for callback in self._done_callbacks:
            _ = cocotb._scheduler.instance.schedule(callback, self)

    @deprecated(
        "Using `task` directly is prefered to `task.join()` in all situations where the latter could be used.`"
    )
    def join(self) -> "cocotb.triggers._Join[ResultType]":
        """Wait for the task to complete.

        Returns:
            A :class:`~cocotb.triggers.Join` trigger which, if awaited, will block until the given Task completes.

        .. code-block:: python3

            my_task = cocotb.start_soon(my_coro())
            await my_task.join()
            # "my_task" is done here

        .. deprecated:: 2.0

            Using ``task`` directly is prefered to ``task.join()`` in all situations where the latter could be used.
        """
        return cocotb.triggers._Join(self)

    @cached_property
    def _join(self) -> cocotb.triggers.Trigger:
        return cocotb.triggers._Join(self)

    def cancel(self, msg: Optional[str] = None) -> None:
        """Cancel a Task's further execution.

        When a Task is cancelled, a :exc:`asyncio.CancelledError` is thrown into the Task.
        """

        if self._state in (TaskState.FINISHED, TaskState.CANCELLED):
            return

        if msg is None:
            self._resume_value = CancelledError()
        else:
            self._resume_value = CancelledError(msg)

        if self._state is TaskState.UNSTARTED:
            # must fail immediately
            self._state = TaskState.CANCELLED
            self._cleanup()

        elif self._state is TaskState.PENDING:
            self._callback_handle.cancel()
            self._schedule_resume()

        elif self._state is TaskState.RUNNING:
            self._schedule_resume()

        else:  # TaskState.SCHEDULED
            pass

    def cancelled(self) -> bool:
        """Return ``True`` if the Task was cancelled."""
        return self._state is TaskState.CANCELLED

    def done(self) -> bool:
        """Return ``True`` if the Task has finished executing."""
        return self._state in (TaskState.FINISHED, TaskState.CANCELLED)

    def result(self) -> ResultType:
        """Return the result of the Task.

        If the Task ran to completion, the result is returned.
        If the Task failed with an exception, the exception is re-raised.
        If the Task was cancelled, the CancelledError is re-raised.
        If the coroutine is not yet complete, a :exc:`asyncio.InvalidStateError` is raised.
        """
        if self._state is TaskState.CANCELLED:
            raise self._cancelled_error
        elif self._state is TaskState.FINISHED:
            return self._result.get()
        else:
            raise InvalidStateError("result is not yet available")

    def exception(self) -> Optional[BaseException]:
        """Return the exception of the Task.

        If the Task ran to completion, ``None`` is returned.
        If the Task failed with an exception, the exception is returned.
        If the Task was cancelled, the CancelledError is re-raised.
        If the coroutine is not yet complete, a :exc:`asyncio.InvalidStateError` is raised.
        """
        if self._state is TaskState.CANCELLED:
            raise self._cancelled_error
        elif self._state is TaskState.FINISHED:
            if isinstance(self._result, Error):
                return self._result.error
            else:
                return None
        else:
            raise InvalidStateError("result is not yet available")

    def _add_done_callback(self, callback: Callable[["Task[ResultType]"], Any]) -> None:
        """Add *callback* to the list of callbacks to be run once the Task becomes "done".

        Args:
            callback: The callback to run once "done".

        .. note::
            If the task is already done, calling this function will call the callback immediately.
        """
        if self.done():
            cocotb._scheduler.instance.schedule(callback, self)
        else:
            self._done_callbacks.append(callback)

    def __await__(self) -> Generator[Any, Any, ResultType]:
        if self._state is TaskState.UNSTARTED:
            self._schedule_resume()
        if not self.done():
            yield self._join
        return self.result()


_all_tasks: Set[Task[Any]] = set()


def all_tasks() -> Set[Task[Any]]:
    return _all_tasks


_current_task: Union[Task[Any], None] = None


def current_task() -> Union[Task[Any], None]:
    return _current_task
