# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import collections.abc
import inspect
import logging
import os
import warnings
from asyncio import CancelledError, InvalidStateError
from enum import auto
from typing import (
    Any,
    Callable,
    Coroutine,
    Generator,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

import cocotb
import cocotb.triggers
from cocotb._deprecation import deprecated
from cocotb._outcomes import Error, Outcome, Value
from cocotb._py_compat import cached_property
from cocotb._utils import DocEnum, extract_coro_stack, remove_traceback_frames

#: Task result type
ResultType = TypeVar("ResultType")

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


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

    def __init__(self, inst):
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

        self._coro: Coroutine = inst
        self._state: _TaskState = _TaskState.UNSTARTED
        self._outcome: Optional[Outcome[ResultType]] = None
        self._trigger: Optional[cocotb.triggers.Trigger] = None
        self._done_callbacks: List[Callable[[Task[Any]], Any]] = []
        self._cancelled_msg: Union[str, None] = None

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

    def _get_coro_stack(self) -> Any:
        """Get the coroutine callstack of this Task."""
        coro_stack = extract_coro_stack(self._coro)

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

    def _advance(self, exc: Union[BaseException, None]) -> Any:
        """Advance to the next yield in this coroutine.

        Args:
            exc: :exc:`BaseException` to throw into the coroutine or nothing.

        Returns:
            The object yielded from the coroutine or ``None`` if coroutine finished.
        """
        self._state = _TaskState.RUNNING
        try:
            if exc is None:
                return self._coro.send(None)
            else:
                return self._coro.throw(exc)
        except StopIteration as e:
            self._outcome = Value(e.value)
            self._state = _TaskState.FINISHED
        except (KeyboardInterrupt, SystemExit):
            # Allow these to bubble up to the execution root to fail the sim immediately.
            # This follows asyncio's behavior.
            raise
        except BaseException as e:
            self._outcome = Error(remove_traceback_frames(e, ["_advance"]))
            self._state = _TaskState.FINISHED

        if self.done():
            self._do_done_callbacks()

    def kill(self) -> None:
        """Kill a coroutine."""
        if self.done():
            # already finished, nothing to kill
            return

        if _debug:
            self._log.debug("kill() called on coroutine")
        # todo: probably better to throw an exception for anyone waiting on the coroutine
        self._outcome = Value(None)
        cocotb._scheduler_inst._unschedule(self)

        # Close coroutine so there is no RuntimeWarning that it was never awaited
        self._coro.close()

        self._state = _TaskState.FINISHED
        self._do_done_callbacks()

    def _do_done_callbacks(self) -> None:
        for callback in self._done_callbacks:
            callback(self)

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
        return self

    def cancel(self, msg: Optional[str] = None) -> None:
        """Cancel a Task's further execution.

        When a Task is cancelled, a :exc:`asyncio.CancelledError` is thrown into the Task.
        """
        if self.done():
            return

        self._cancelled_msg = msg
        warnings.warn(
            "Calling this method will cause a CancelledError to be thrown in the "
            "Task sometime in the future.",
            FutureWarning,
            stacklevel=2,
        )
        cocotb._scheduler_inst._unschedule(self)

        # Close coroutine so there is no RuntimeWarning that it was never awaited
        self._coro.close()

        self._state = _TaskState.CANCELLED
        self._do_done_callbacks()

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
            return self._outcome.get()
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

    def __await__(self) -> Generator[Any, Any, ResultType]:
        if self._state is _TaskState.UNSTARTED:
            cocotb._scheduler_inst._schedule_task_internal(self)
            yield self.complete
        elif not self.done():
            yield self.complete
        return self.result()
