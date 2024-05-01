# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import collections.abc
import inspect
import logging
from asyncio import CancelledError, InvalidStateError
from typing import Any, Coroutine, Generator, Generic, Optional, TypeVar

import cocotb
import cocotb.triggers
from cocotb._outcomes import Error, Outcome, Value
from cocotb._py_compat import cached_property
from cocotb.utils import extract_coro_stack, remove_traceback_frames

T = TypeVar("T")


class CancellationError(Exception):
    """Result of a cancelled Task when cancellation exits abnormally."""

    def __init__(self, msg: str, outcome: Outcome) -> None:
        super().__init__(msg)
        self.outcome = outcome


class Task(Generic[T]):
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

    _name: str = "Task"  # class name of schedulable task
    _id_count = 0  # used by the scheduler for debug

    def __init__(self, inst):
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
        elif not isinstance(inst, collections.abc.Coroutine):
            raise TypeError(f"{inst} isn't a valid coroutine!")

        self._coro: Coroutine = inst
        self._started: bool = False
        self._outcome: Optional[Outcome[T]] = None
        self._trigger: Optional[cocotb.triggers.Trigger] = None
        self._cancelled: Optional[CancelledError] = None

        self._task_id = self._id_count
        type(self)._id_count += 1
        self.__name__ = f"{type(self)._name} {self._task_id}"
        self.__qualname__ = self.__name__

    @cached_property
    def log(self) -> logging.Logger:
        # Creating a logger is expensive, only do it if we actually plan to
        # log anything
        return logging.getLogger(
            f"cocotb.{self.__qualname__}.{self._coro.__qualname__}"
        )

    def __str__(self) -> str:
        return f"<{self.__name__}>"

    def _get_coro_stack(self) -> Any:
        """Get the coroutine callstack of this Task."""
        coro_stack = extract_coro_stack(self._coro)

        # Remove Trigger.__await__() from the stack, as it's not really useful
        if len(coro_stack) > 0 and coro_stack[-1].name == "__await__":
            coro_stack.pop()

        return coro_stack

    def __repr__(self) -> str:
        coro_stack = self._get_coro_stack()

        if cocotb._scheduler._current_task is self:
            fmt = "<{name} running coro={coro}()>"
        elif self.done():
            fmt = "<{name} finished coro={coro}() outcome={outcome}>"
        elif self._trigger is not None:
            fmt = "<{name} pending coro={coro}() trigger={trigger}>"
        elif not self._started:
            fmt = "<{name} created coro={coro}()>"
        else:
            raise RuntimeError("Task in unknown state")

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

        repr_string = fmt.format(
            name=self.__name__,
            coro=coro_name,
            trigger=self._trigger,
            outcome=self._outcome,
        )
        return repr_string

    def _advance(self, outcome: Outcome) -> Optional["cocotb.triggers.Trigger"]:
        """Advance to the next yield in this coroutine.

        Args:
            outcome: The :any:`outcomes.Outcome` object to resume with.

        Returns:
            The object yielded from the coroutine or None if coroutine finished

        """
        try:
            self._started = True
            return outcome.send(self._coro)
        except StopIteration as e:
            self._outcome = Value(e.value)
        except BaseException as e:
            self._outcome = Error(remove_traceback_frames(e, ["_advance", "send"]))

    def kill(self) -> None:
        """Stop a Task without throwing a :exc:`asyncio.CancelledError`.

        .. deprecated:: 2.0

            Replaced by :meth:`cancel`.
        """
        if self.done():
            return

        self._outcome = Value(None)
        cocotb._scheduler._unschedule(self)

    def join(self) -> "cocotb.triggers.Join":
        """Return a trigger that will fire when the wrapped coroutine exits."""
        return cocotb.triggers.Join(self)

    def has_started(self) -> bool:
        """Return ``True`` if the Task has started executing."""
        return self._started

    def cancel(self, msg: Optional[str] = None) -> None:
        """Cancel a Task's further execution.

        When a Task is cancelled, a :exc:`asyncio.CancelledError` is thrown into the Task.
        """
        if self.done():
            return

        if not self._started:
            # don't throw CancelledError into unstarted task, there's no way to catch it
            self._outcome = Value(None)
            if self in cocotb._scheduler._pending_tasks:
                # unschedule if scheduled
                cocotb._scheduler._unschedule(self)
        else:
            self._cancelled = CancelledError(msg)
            try:
                self._coro.throw(self._cancelled)
            except CancelledError as e:
                if e is self._cancelled:
                    self._outcome = Value(None)
                else:
                    self._outcome = Error(
                        CancellationError(
                            "Task was cancelled, but raised another exception.",
                            Error(remove_traceback_frames(e, ["cancel", "send"])),
                        )
                    )
            except StopIteration as e:
                self._outcome = Error(
                    CancellationError(
                        "Task was cancelled, but exited normally.", Value(e.value)
                    )
                )
            except BaseException as e:
                self._outcome = Error(
                    CancellationError(
                        "Task was cancelled, but raised another exception.",
                        Error(remove_traceback_frames(e, ["cancel", "send"])),
                    )
                )
            else:
                self._outcome = Error(
                    CancellationError(
                        "Task was cancelled, but continued running.", Value(None)
                    )
                )
            finally:
                cocotb._scheduler._unschedule(self)

    def cancelled(self) -> bool:
        """Return ``True`` if the Task was cancelled."""
        return self._cancelled is not None

    def done(self) -> bool:
        """Return ``True`` if the Task has finished executing."""
        return self._outcome is not None or self.cancelled()

    def result(self) -> T:
        """Return the result of the Task.

        If the Task ran to completion, the result is returned.
        If the Task failed with an exception, the exception is re-raised.
        If the Task was cancelled, the CancelledError is re-raised.
        If the coroutine is not yet complete, a :exc:`asyncio.InvalidStateError` is raised.
        """
        if not self.done():
            raise InvalidStateError("result is not yet available")
        elif self.cancelled():
            raise self._cancelled
        else:
            return self._outcome.get()

    def exception(self) -> Optional[BaseException]:
        """Return the exception of the Task.

        If the Task ran to completion, ``None`` is returned.
        If the Task failed with an exception, the exception is returned.
        If the Task was cancelled, the CancelledError is re-raised.
        If the coroutine is not yet complete, a :exc:`asyncio.InvalidStateError` is raised.
        """
        if not self.done():
            raise InvalidStateError("result is not yet available")
        elif self.cancelled():
            raise self._cancelled
        elif isinstance(self._outcome, Error):
            return self._outcome.error
        else:
            return None

    def __await__(self) -> Generator[Any, Any, T]:
        # It's tempting to use `return (yield from self._coro)` here,
        # which bypasses the scheduler. Unfortunately, this means that
        # we can't keep track of the result or state of the coroutine,
        # things which we expose in our public API. If you want the
        # efficiency of bypassing the scheduler, remove the `@coroutine`
        # decorator from your `async` functions.

        # Hand the coroutine back to the scheduler trampoline.
        return (yield self)


class _RunningTest(Task[None]):
    """
    The result of calling a :class:`cocotb.test` decorated object.

    All this class does is change ``__name__`` to show "Test" instead of "Task".

    .. versionchanged:: 1.8.0
        Moved to the ``cocotb.task`` module.
    """

    _name: str = "Test"

    def __init__(self, inst: Coroutine[Any, Any, None], name: str) -> None:
        super().__init__(inst)
        self.__name__ = f"{type(self)._name} {name}"
        self.__qualname__ = self.__name__
