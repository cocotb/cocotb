# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import collections.abc
import inspect
import logging
import os
import traceback
from asyncio import CancelledError, InvalidStateError
from enum import auto
from types import CoroutineType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Coroutine,
    Generator,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
    cast,
)

import cocotb
from cocotb._base_triggers import Trigger
from cocotb._deprecation import deprecated
from cocotb._outcomes import Error, Outcome, Value
from cocotb._py_compat import cached_property
from cocotb._utils import DocEnum, extract_coro_stack, remove_traceback_frames

if TYPE_CHECKING:
    from typing import Self

#: Task result type
ResultType = TypeVar("ResultType")

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


class CancellationError(Exception):
    """Result of a cancelled Task when cancellation exits abnormally."""

    def __init__(self, msg: str, outcome: Outcome[Any]) -> None:
        super().__init__(msg)
        self.outcome = outcome


class _TaskState(DocEnum):
    """State of a Task."""

    UNSTARTED = (auto(), "Task created, but never run and not scheduled")
    SCHEDULED = (auto(), "Task queued to run soon")
    PENDING = (auto(), "Task waiting for Trigger to fire")
    RUNNING = (auto(), "Task is currently running")
    FINISHED = (auto(), "Task has finished with a value or Exception")
    CANCELLED = (auto(), "Task was cancelled before it finished")


class Task(Generic[ResultType]):
    """Concurrently executing task.

    This class is not intended for users to directly instantiate.
    Use :func:`cocotb.create_task` to create a Task object
    or :func:`cocotb.start_soon` to create a Task and schedule it to run.

    .. versionchanged:: 1.8
        Moved to the ``cocotb.task`` module.

    .. versionchanged:: 2.0
        The ``retval``, ``_finished``, and ``__bool__`` methods were removed.
        Use :meth:`result`, :meth:`done`, and :meth:`done` methods instead, respectively.
    """

    _id_count = 0  # used by the scheduler for debug

    def __init__(self, inst: Coroutine[Trigger, None, ResultType]) -> None:
        if inspect.iscoroutinefunction(inst):
            raise TypeError(
                f"Coroutine function {inst} should be called prior to being scheduled."
            )
        elif inspect.isasyncgen(inst):
            raise TypeError(
                f"{inst.__qualname__} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await."
            )
        elif not isinstance(inst, collections.abc.Coroutine):
            raise TypeError(f"{inst} isn't a valid coroutine!")

        self._coro = inst
        self._state: _TaskState = _TaskState.UNSTARTED
        self._outcome: Union[Outcome[ResultType], None] = None
        self._trigger: Union[Trigger, None] = None
        self._done_callbacks: List[Callable[[Task[ResultType]], Any]] = []
        self._cancelled_msg: Union[str, None] = None
        self._must_cancel: bool = False
        self._has_resumed: bool = False

        self._task_id = self._id_count
        type(self)._id_count += 1
        self._name = f"Task {self._task_id}"

    @cached_property
    def _cancelled_error(self) -> CancelledError:
        if self._cancelled_msg is None:
            return CancelledError()
        else:
            return CancelledError(self._cancelled_msg)

    @cached_property
    def _log(self) -> logging.Logger:
        return logging.getLogger(f"cocotb.{self._name}.{self._coro.__qualname__}")

    def __str__(self) -> str:
        # TODO Do we really need this?
        return f"<{self._name}>"

    def _get_coro_stack(self) -> traceback.StackSummary:
        """Get the coroutine callstack of this Task.

        Assumes :attr:`_coro` is a native Python coroutine object.

        Raises:
            TypeError: If :attr:`_coro` is not a native Python coroutine object.
        """
        coro_stack = extract_coro_stack(
            cast("CoroutineType[Trigger, None, ResultType]", self._coro)
        )

        # Remove Trigger.__await__() from the stack, as it's not really useful
        if len(coro_stack) > 0 and coro_stack[-1].name == "__await__":
            coro_stack.pop()

        return coro_stack

    def __repr__(self) -> str:
        if inspect.iscoroutine(self._coro):
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
            coro_name = type(self._coro).__name__

        if self._state is _TaskState.RUNNING:
            return f"<{self._name} running coro={coro_name}()>"
        elif self._state is _TaskState.FINISHED:
            return f"<{self._name} finished coro={coro_name}() outcome={self._outcome}>"
        elif self._state is _TaskState.PENDING:
            return f"<{self._name} pending coro={coro_name}() trigger={self._trigger}>"
        elif self._state is _TaskState.SCHEDULED:
            return f"<{self._name} scheduled coro={coro_name}()>"
        elif self._state is _TaskState.UNSTARTED:
            return f"<{self._name} created coro={coro_name}()>"
        elif self._state is _TaskState.CANCELLED:
            return f"<{self._name} cancelled coro={coro_name} with={self._cancelled_error} outcome={self._outcome}"
        else:
            raise RuntimeError("Task in unknown state")

    def _set_outcome(
        self, result: Outcome[ResultType], state: _TaskState = _TaskState.FINISHED
    ) -> None:
        self._outcome = result
        self._state = state

        # Run done callbacks.
        for callback in self._done_callbacks:
            callback(self)

        # Wake up waiting Tasks.
        cocotb._scheduler_inst._react(self.complete)
        cocotb._scheduler_inst._react(self._join)

    def _advance(self, exc: Union[BaseException, None]) -> Union[Trigger, None]:
        """Resume execution of the Task.

        Runs until the coroutine ends, raises, or yields a Trigger.
        Can optionally throw an Exception into the Task.

        Args:
            exc: :exc:`BaseException` to throw into the coroutine or nothing.

        Returns:
            The object yielded from the coroutine or ``None`` if coroutine finished.
        """
        self._state = _TaskState.RUNNING

        if not self._has_resumed:
            self._has_resumed = True
            cocotb._scheduler_inst._react(self.started)

        if self._must_cancel:
            exc = self._cancelled_error

        try:
            if exc is None:
                trigger = self._coro.send(None)
            else:
                trigger = self._coro.throw(exc)
        except StopIteration as e:
            outcome = Value(e.value)
            if self._must_cancel:
                self._set_outcome(
                    Error(
                        CancellationError(
                            "Task was cancelled, but exited normally. Did you forget to re-raise the CancelledError?",
                            outcome,
                        )
                    )
                )
            else:
                self._set_outcome(outcome)
            return None
        except (KeyboardInterrupt, SystemExit):
            # Allow these to bubble up to the execution root to fail the sim immediately.
            # This follows asyncio's behavior.
            raise
        except CancelledError as e:
            self._set_outcome(
                Error(remove_traceback_frames(e, ["_advance"])), _TaskState.CANCELLED
            )
            return None
        except BaseException as e:
            self._set_outcome(Error(remove_traceback_frames(e, ["_advance"])))
            return None
        else:
            if self._must_cancel:
                self._set_outcome(
                    Error(
                        CancellationError(
                            "Task was cancelled, but continued running. Did you forget to re-raise the CancelledError?",
                            Value(None),
                        )
                    )
                )
                return None
            else:
                return trigger

    def kill(self) -> None:
        """Kill a coroutine."""
        if self.done():
            return

        if self._state is _TaskState.UNSTARTED:
            self._coro.close()
        elif self._state is _TaskState.RUNNING:
            raise RuntimeError("Can't kill currently running Task")
        else:
            # unschedule if scheduled and unprime triggers if pending
            cocotb._scheduler_inst._unschedule(self)

        self._set_outcome(Value(None))  # type: ignore  # `kill()` sets the result to None regardless of the ResultType

    @cached_property
    def started(self) -> "TaskStarted[ResultType]":
        """Trigger which fires after the first time the Task resumes.

        Mostly useful as a way to emulate :func:`cocotb.start` and ``cocotb.fork``'s behavior of returning after the Task has started running.

        .. code-block:: python

            task = cocotb.start_soon(coro())
            await task.started
        """
        return TaskStarted._make(self)

    @cached_property
    def complete(self) -> "TaskComplete[ResultType]":
        r"""Trigger which fires when the Task completes.

        Unlike :meth:`join`, this Trigger does not return the result of the Task when :keyword:`await`\ ed.

        .. code-block:: python

            async def coro_inner():
                await Timer(1, unit="ns")
                raise ValueError("Oops")


            task = cocotb.start_soon(coro_inner())
            await task.complete  # no exception raised here
            assert task.exception() == ValueError("Oops")
        """
        return TaskComplete._make(self)

    @deprecated(
        "Using `task` directly is prefered to `task.join()` in all situations where the latter could be used."
    )
    def join(self) -> "Join[ResultType]":
        r"""Block until the Task completes and return the result.

        Equivalent to calling :class:`Join(self) <cocotb.triggers.Join>`.

        .. code-block:: python

            async def coro_inner():
                await Timer(1, unit="ns")
                return "Hello world"


            task = cocotb.start_soon(coro_inner())
            result = await task.join()
            assert result == "Hello world"

        Returns:
            Object that can be :keyword:`await`\ ed or passed into :class:`~cocotb.triggers.First` or :class:`~cocotb.triggers.Combine`;
            the result of which will be the result of the Task.

        .. deprecated:: 2.0
            Using ``task`` directly is preferred to ``task.join()`` in all situations where the latter could be used.
        """
        return self._join

    @cached_property
    def _join(self) -> "Join[ResultType]":
        return Join._make(self)

    def cancel(self, msg: Optional[str] = None) -> bool:
        """Cancel a Task's further execution.

        When a Task is cancelled, a :exc:`asyncio.CancelledError` is thrown into the Task.

        Returns: ``True`` if the Task was cancelled; ``False`` otherwise.
        """
        if self.done():
            return False

        self._cancelled_msg = msg
        self._must_cancel = True

        if self._state is _TaskState.UNSTARTED:
            self._coro.close()
            # must fail immediately
            self._set_outcome(Error(self._cancelled_error), _TaskState.CANCELLED)

        elif self._state is _TaskState.PENDING:
            # unprime triggers if pending
            cocotb._scheduler_inst._unschedule(self)
            # schedule wakeup to throw CancelledError
            cocotb._scheduler_inst._schedule_task_internal(self)

        elif self._state is _TaskState.RUNNING:
            # Reschedule to throw CancelledError
            cocotb._scheduler_inst._schedule_task_internal(self)

        return True

    def cancelled(self) -> bool:
        """Return ``True`` if the Task was cancelled."""
        return self._state is _TaskState.CANCELLED

    def done(self) -> bool:
        """Return ``True`` if the Task has finished executing."""
        return self._state in (_TaskState.FINISHED, _TaskState.CANCELLED)

    def result(self) -> ResultType:
        """Return the result of the Task.

        If the Task ran to completion, the result is returned.
        If the Task failed with an exception, the exception is re-raised.
        If the Task was cancelled, the :exc:`asyncio.CancelledError` is re-raised.
        If the coroutine is not yet complete, an :exc:`asyncio.InvalidStateError` is raised.
        """
        if self._state is _TaskState.CANCELLED:
            raise self._cancelled_error
        elif self._state is _TaskState.FINISHED:
            return cast(Outcome[ResultType], self._outcome).get()
        else:
            raise InvalidStateError("result is not yet available")

    def exception(self) -> Optional[BaseException]:
        """Return the exception of the Task.

        If the Task ran to completion, ``None`` is returned.
        If the Task failed with an exception, the exception is returned.
        If the Task was cancelled, the :exc:`asyncio.CancelledError` is re-raised.
        If the coroutine is not yet complete, an :exc:`asyncio.InvalidStateError` is raised.
        """
        if self._state is _TaskState.CANCELLED:
            raise self._cancelled_error
        elif self._state is _TaskState.FINISHED:
            if isinstance(self._outcome, Error):
                return self._outcome.error
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
            callback(self)
        self._done_callbacks.append(callback)

    def __await__(self) -> Generator[Trigger, None, ResultType]:
        if self._state is _TaskState.UNSTARTED:
            cocotb._scheduler_inst._schedule_task_internal(self)
            yield self.complete
        elif not self.done():
            yield self.complete
        return self.result()


class _TaskTriggerBase(Trigger, Generic[ResultType]):
    _task_attr: ClassVar[str]
    _task: Task[ResultType]

    def __new__(cls, task: Task[ResultType]) -> "TaskComplete[ResultType]":
        raise NotImplementedError(
            f"{cls.__qualname__} cannot be instantiated. Use the `Task.{cls._task_attr}` attribute."
        )

    def __init__(self, task: Task[ResultType]) -> None:
        pass

    @classmethod
    def _make(cls, task: Task[ResultType]) -> "Self":
        self = super().__new__(cls)
        super().__init__(self)
        self._task = task
        return self

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._task!s})"

    @property
    def task(self) -> Task[ResultType]:
        """The :class:`.Task` associated with this completion event."""
        return self._task


class TaskStarted(_TaskTriggerBase[ResultType]):
    """Trigger which fires after the first time the Task resumes.

    See :attr:`.Task.started` for more info.

    .. warning::
        This class cannot be instantiated in the normal way.
        You must use :attr:`.Task.started`.

    .. versionadded:: 2.0
    """

    _task_attr = "started"

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._task._has_resumed:
            callback(self)
        else:
            super()._prime(callback)


class TaskComplete(_TaskTriggerBase[ResultType]):
    r"""Fires when a :class:`~cocotb.task.Task` completes.

    Unlike :class:`~cocotb.triggers.Join`, this Trigger does not return the result of the Task when :keyword:`await`\ ed.
    See :attr:`.Task.complete` for more information.

    .. warning::
        This class cannot be instantiated in the normal way.
        You must use :attr:`.Task.complete`.

    .. versionadded:: 2.0
    """

    _task_attr = "complete"

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._task.done():
            callback(self)
        else:
            super()._prime(callback)


class Join(TaskComplete[ResultType]):
    r"""Fires when a :class:`~cocotb.task.Task` completes and returns the Task's result.

    Equivalent to calling :meth:`task.join() <cocotb.task.Task.join>`.

    .. code-block:: python

        async def coro_inner():
            await Timer(1, unit="ns")
            return "Hello world"


        task = cocotb.start_soon(coro_inner())
        result = await Join(task)
        assert result == "Hello world"

    Args:
        task: The Task upon which to wait for completion.

    Returns:
        Object that can be :keyword:`await`\ ed or passed into :class:`~cocotb.triggers.First` or :class:`~cocotb.triggers.Combine`;
        the result of which will be the result of the Task.

    .. deprecated:: 2.0
        Using ``task`` directly is preferred to ``Join(task)`` in all situations where the latter could be used.
    """

    @deprecated(
        "Using `task` directly is prefered to `Join(task)` in all situations where the latter could be used."
    )
    def __new__(cls, task: Task[ResultType]) -> "Join[ResultType]":
        return task._join

    def __await__(self) -> Generator["Self", None, ResultType]:  # type: ignore[override]
        yield self
        return self._task.result()
