# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import collections.abc
import inspect
import logging
import traceback
from asyncio import CancelledError, InvalidStateError
from bdb import BdbQuit
from enum import auto
from types import CoroutineType
from typing import (
    AbstractSet,
    Any,
    Callable,
    Coroutine,
    Generator,
    Generic,
    List,
    Optional,
    Set,  # noqa: F401  # Needed for comment type annotations
    TypeVar,
    Union,
    cast,
)

import cocotb
import cocotb.event_loop
import cocotb.triggers
from cocotb._deprecation import deprecated
from cocotb._outcomes import Error, Outcome, Value
from cocotb._py_compat import cached_property
from cocotb._utils import DocEnum, extract_coro_stack, remove_traceback_frames


class CancellationError(Exception):
    """Result of a cancelled Task when cancellation exits abnormally."""

    def __init__(self, msg: str, outcome: Outcome[Any]) -> None:
        super().__init__(msg)
        self.outcome = outcome


class _TaskState(DocEnum):
    """State of a Task."""

    UNSTARTED = (auto(), "Task created, but never run and not scheduled")
    SCHEDULED = (auto(), "Task in Scheduler queue to run soon")
    PENDING = (auto(), "Task waiting for Trigger to fire")
    RUNNING = (auto(), "Task is currently running")
    FINISHED = (auto(), "Task has finished with a value or Exception")
    CANCELLED = (auto(), "Task was cancelled before it finished")


#: Task result type
ResultType = TypeVar("ResultType")


class Task(Generic[ResultType]):
    """Concurrently executing task.

    This class is not intended for users to directly instantiate.
    Use :func:`cocotb.create_task` to create a Task object,
    or use :func:`cocotb.start_soon` or :func:`cocotb.start` to
    create a Task and schedule it to run.

    .. versionchanged:: 1.8
        Moved to the ``cocotb.task`` module.

    .. versionchanged:: 2.0
        The ``retval``, ``_finished``, and ``__bool__`` methods were removed.
        Use :meth:`result`, :meth:`done`, and :meth:`done` methods instead, respectively.
    """

    _id_count = 0  # used by the scheduler for debug

    def __init__(
        self, inst: Coroutine["cocotb.triggers.Trigger", None, ResultType]
    ) -> None:
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

        self._coro: Coroutine[cocotb.triggers.Trigger, None, ResultType] = inst
        self._state: _TaskState = _TaskState.UNSTARTED
        self._result: Union[Outcome[ResultType], None] = None
        self._callback_handle: Union[
            cocotb.triggers.CallbackHandle, cocotb.event_loop.CallbackHandle, None
        ] = None
        self._done_callbacks: List[Callable[[Task[Any]], Any]] = []
        self._cancelled_error: Union[CancelledError, None] = None
        self._must_cancel: bool = False

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
        """Get the coroutine callstack of this Task.

        Assumes :attr:`_coro` is a native coroutine object.
        """

        coro_stack = extract_coro_stack(
            cast("CoroutineType[cocotb.triggers.Trigger, None, ResultType]", self._coro)
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
            # TODO is repr appropriate here?
            coro_name = repr(self._coro)

        if self._state is _TaskState.RUNNING:
            return f"<{self.name} running coro={coro_name}()>"
        elif self._state is _TaskState.FINISHED:
            return f"<{self.name} finished coro={coro_name}() outcome={self._result}>"
        elif self._state is _TaskState.PENDING:
            trigger = cast(
                cocotb.triggers.CallbackHandle, self._callback_handle
            )._trigger
            return f"<{self.name} pending coro={coro_name}() trigger={trigger}>"
        elif self._state is _TaskState.SCHEDULED:
            return f"<{self.name} scheduled coro={coro_name}()>"
        elif self._state is _TaskState.UNSTARTED:
            return f"<{self.name} created coro={coro_name}()>"
        elif self._state is _TaskState.CANCELLED:
            return (
                f"<{self.name} cancelled coro={coro_name} with={self._cancelled_error}"
            )
        else:
            raise RuntimeError("Task in unknown state")

    def _set_result(
        self, result: Outcome[ResultType], state: _TaskState = _TaskState.FINISHED
    ) -> None:
        self._result = result
        self._state = state

        # Close coroutine so there is no RuntimeWarning that it was never awaited
        self._coro.close()

        # schedule callbacks for things waiting for finish
        self.complete._react()
        for callback in self._done_callbacks:
            callback(self)

    def _schedule_resume(self, exc: Union[BaseException, None] = None) -> None:
        """Schedule the Task to resume execution."""
        self._callback_handle = cocotb.event_loop._instance.schedule(self._resume, exc)
        self._state = _TaskState.SCHEDULED

    def _resume(self, exc: Union[BaseException, None] = None) -> None:
        """Resume execution of the Task.

        Runs until the coroutine ends, raises, or yields a Trigger.

        Args:
            exc: A :exc:`BaseException` to throw into the coroutine or nothing.

        Returns:
            The object yielded from the coroutine or None if coroutine finished
        """
        self._state = _TaskState.RUNNING
        global _current_task
        _current_task = self

        if self._must_cancel:
            exc = self._make_cancelled_error()

        # Run coroutine with the resume value
        try:
            if exc is None:
                result = self._coro.send(None)
            else:
                result = self._coro.throw(exc)
        except StopIteration as e:
            outcome = Value(e.value)
            if self._must_cancel:
                breakpoint()
                return self._set_result(
                    Error(
                        CancellationError(
                            "Task was cancelled, but exited normally. Did you forget to re-raise the CancelledError?",
                            outcome,
                        )
                    )
                )
            else:
                return self._set_result(outcome)
        except (KeyboardInterrupt, SystemExit, BdbQuit):
            # Allow these to bubble up to the execution root to fail the sim immediately.
            # This follow's asyncio's behavior.
            raise
        except CancelledError as e:
            return self._set_result(
                Error(remove_traceback_frames(e, ["_resume"])), _TaskState.CANCELLED
            )
        except BaseException as e:
            return self._set_result(Error(remove_traceback_frames(e, ["_resume"])))
        else:
            if self._must_cancel:
                breakpoint()
                return self._set_result(
                    Error(
                        CancellationError(
                            "Task was cancelled, but continued running. Did you forget to re-raise the CancelledError?",
                            Value(None),
                        )
                    )
                )
        finally:
            _current_task = None

        # Check we have a Trigger and provide a more informative error message if not
        if not isinstance(result, cocotb.triggers.Trigger):
            return self._schedule_resume(
                exc=TypeError(
                    f"cocotb scheduler can only handle Triggers, got {type(result).__qualname__}"
                )
            )
        trigger = result

        # Try to register the Task to resume when the Trigger fires
        try:
            self._callback_handle = trigger.register(self._schedule_resume)
        except Exception as e:
            remove_traceback_frames(e, ["_resume", "_register"])
            return self._schedule_resume(exc=e)
        else:
            self._state = _TaskState.PENDING

    def _add_done_callback(self, callback: Callable[["Task[ResultType]"], Any]) -> None:
        """Add *callback* to the list of callbacks to be run once the Task becomes "done".

        Args:
            callback: The callback to run once "done".

        .. note::
            If the task is already done, calling this function will call the callback immediately.
        """
        if self.done():
            cocotb.event_loop._instance.schedule(callback, self)
        else:
            self._done_callbacks.append(callback)

    def _make_cancelled_error(self) -> CancelledError:
        if self._cancelled_error is None:
            self._cancelled_error = CancelledError(self._cancel_message)
        return self._cancelled_error

    @deprecated("Use `task.cancel()` instead.")
    def kill(self) -> None:
        """Kill a coroutine."""
        if self.done():
            return

        if self._state is _TaskState.UNSTARTED:
            pass

        elif self._state is _TaskState.PENDING:
            cast(cocotb.triggers.CallbackHandle, self._callback_handle).cancel()

        elif self._state is _TaskState.SCHEDULED:
            cast(cocotb.event_loop.CallbackHandle, self._callback_handle).cancel()

        elif self._state is _TaskState.RUNNING:
            raise RuntimeError("Can't kill currently running Task")

        result = Value(None)
        self._set_result(result)  # type: ignore  # `kill()` sets the result to None regardless of the ResultType

    @cached_property
    def complete(self) -> "cocotb.triggers.TaskComplete[ResultType]":
        r"""Trigger which fires when the Task completes."""
        return cocotb.triggers.TaskComplete._make(self)

    @deprecated(
        "Using `task` directly is prefered to `task.join()` in all situations where the latter could be used."
    )
    def join(self) -> "Task[ResultType]":
        r"""Block until the Task completes and return the result.

        Equivalent to calling :func:`Join(self) <cocotb.triggers.Join>`.

        .. code-block:: python

            async def coro_inner():
                await Timer(1, units="ns")
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
        return self

    def cancel(self, msg: Optional[str] = None) -> bool:
        """Cancel a Task's further execution.

        When a Task is cancelled, a :exc:`asyncio.CancelledError` is thrown into the Task.

        Returns: ``True`` if the Task was cancelled; ``False`` otherwise.
        """
        if self.done():
            return False

        self._cancel_message = msg
        self._must_cancel = True

        if self._state is _TaskState.UNSTARTED:
            # must fail immediately
            self._set_result(Error(self._make_cancelled_error()), _TaskState.CANCELLED)

        elif self._state is _TaskState.PENDING:
            cast(cocotb.triggers.CallbackHandle, self._callback_handle).cancel()
            self._schedule_resume()

        elif self._state is _TaskState.RUNNING:
            self._schedule_resume()

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
            raise self._make_cancelled_error()
        elif self._state is _TaskState.FINISHED:
            return cast(Outcome[ResultType], self._result).get()
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
            raise self._make_cancelled_error()
        elif self._state is _TaskState.FINISHED:
            if isinstance(self._result, Error):
                return self._result.error
            else:
                return None
        else:
            raise InvalidStateError("result is not yet available")

    def __await__(self) -> Generator[Any, Any, ResultType]:
        if self._state is _TaskState.UNSTARTED:
            self._schedule_resume()
            yield self.complete
        elif not self.done():
            yield self.complete
        return self.result()


# TODO Use normal type annotations once we're on Python 3.8
_all_tasks = set()  # type: Set[Task[Any]]


def all_tasks() -> AbstractSet[Task[Any]]:
    return frozenset(_all_tasks)


# TODO Use normal type annotations once we're on Python 3.8
_current_task = None  # type: Union[Task[Any], None]


def current_task() -> Task[Any]:
    if _current_task is None:
        raise RuntimeError("No task is currently running")
    return _current_task
