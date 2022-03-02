# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import collections.abc
import inspect
import os
import typing
import warnings
from asyncio import CancelledError, InvalidStateError

import cocotb
import cocotb.triggers
from cocotb import outcomes
from cocotb.log import SimLog
from cocotb.result import ReturnValue
from cocotb.utils import extract_coro_stack, lazy_property, remove_traceback_frames

T = typing.TypeVar("T")
Self = typing.TypeVar("Self")

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


class Task(typing.Coroutine[typing.Any, typing.Any, T]):
    """Concurrently executing task.

    This class is not intended for users to directly instantiate.
    Use :func:`cocotb.create_task` to create a Task object,
    or use :func:`cocotb.start_soon` or :func:`cocotb.start` to
    create a Task and schedule it to run.

    .. versionchanged:: 1.8.0
        Moved to the ``cocotb.task`` module.
    """

    _name: str = "Task"  # class name of schedulable task
    _id_count = 0  # used by the scheduler for debug

    def __init__(self, inst):

        if isinstance(inst, collections.abc.Coroutine):
            self._natively_awaitable = True
        elif inspect.isgenerator(inst):
            self._natively_awaitable = False
        elif inspect.iscoroutinefunction(inst):
            raise TypeError(
                "Coroutine function {} should be called prior to being "
                "scheduled.".format(inst)
            )
        elif inspect.isasyncgen(inst):
            raise TypeError(
                "{} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await.".format(
                    inst.__qualname__
                )
            )
        else:
            raise TypeError(
                f"{inst} isn't a valid coroutine! Did you forget to use the yield keyword?"
            )
        self._coro = inst
        self._started = False
        self._outcome: outcomes.Outcome = None
        self._trigger: typing.Optional[cocotb.triggers.Trigger] = None
        self._cancelled: typing.Optional[CancelledError] = None

        self._task_id = self._id_count
        type(self)._id_count += 1
        self.__name__ = f"{type(self)._name} {self._task_id}"
        self.__qualname__ = self.__name__

    @lazy_property
    def log(self) -> SimLog:
        # Creating a logger is expensive, only do it if we actually plan to
        # log anything
        return SimLog(f"cocotb.{self.__qualname__}.{self._coro.__qualname__}")

    @property
    def retval(self) -> T:
        """Return the result of the Task.

        If the Task ran to completion, the result is returned.
        If the Task failed with an exception, the exception is re-raised.
        If the Task is not yet complete, a :exc:`RuntimeError` is raised.

        .. deprecated:: 1.7.0
        """
        warnings.warn(
            "Deprecated in favor of the result() method. "
            "Replace `task.retval` with `task.result()`.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self._outcome is None:
            raise RuntimeError("coroutine is not complete")
        return self._outcome.get()

    @property
    def _finished(self) -> bool:
        """``True`` if the Task is finished executing.

        .. deprecated:: 1.7.0
        """
        warnings.warn(
            "Deprecated in favor of the done() method. "
            "Replace `task._finished` with `task.done()`.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._outcome is not None

    def __iter__(self: Self) -> Self:
        # for use in "yield from" statements
        return self

    def __str__(self) -> str:
        return f"<{self.__name__}>"

    def _get_coro_stack(self) -> typing.Any:
        """Get the coroutine callstack of this Task."""
        coro_stack = extract_coro_stack(self._coro)

        # Remove Trigger.__await__() from the stack, as it's not really useful
        if self._natively_awaitable and len(coro_stack):
            if coro_stack[-1].name == "__await__":
                coro_stack.pop()

        return coro_stack

    def __repr__(self) -> str:
        coro_stack = self._get_coro_stack()

        if cocotb.scheduler._current_task is self:
            fmt = "<{name} running coro={coro}()>"
        elif self.done():
            fmt = "<{name} finished coro={coro}() outcome={outcome}>"
        elif self._trigger is not None:
            fmt = "<{name} pending coro={coro}() trigger={trigger}>"
        elif not self._started:
            fmt = "<{name} created coro={coro}()>"
        else:
            fmt = "<{name} adding coro={coro}()>"

        try:
            coro_name = coro_stack[-1].name
        # coro_stack may be empty if:
        # - exhausted generator
        # - finished coroutine
        except IndexError:
            coro_name = self._coro.__name__

        repr_string = fmt.format(
            name=self.__name__,
            coro=coro_name,
            trigger=self._trigger,
            outcome=self._outcome,
        )
        return repr_string

    def _advance(self, outcome: outcomes.Outcome) -> typing.Any:
        """Advance to the next yield in this coroutine.

        Args:
            outcome: The :any:`outcomes.Outcome` object to resume with.

        Returns:
            The object yielded from the coroutine or None if coroutine finished

        """
        try:
            self._started = True
            return outcome.send(self._coro)
        except ReturnValue as e:
            self._outcome = outcomes.Value(e.retval)
        except StopIteration as e:
            self._outcome = outcomes.Value(e.value)
        except BaseException as e:
            self._outcome = outcomes.Error(
                remove_traceback_frames(e, ["_advance", "send"])
            )

    def send(self, value: typing.Any) -> typing.Any:
        return self._coro.send(value)

    def throw(self, exc: BaseException) -> typing.Any:
        return self._coro.throw(exc)

    def close(self) -> None:
        return self._coro.close()

    def kill(self) -> None:
        """Kill a coroutine."""
        if self._outcome is not None:
            # already finished, nothing to kill
            return

        if _debug:
            self.log.debug("kill() called on coroutine")
        # todo: probably better to throw an exception for anyone waiting on the coroutine
        self._outcome = outcomes.Value(None)
        cocotb.scheduler._unschedule(self)

    def join(self) -> "cocotb.triggers.Join":
        """Return a trigger that will fire when the wrapped coroutine exits."""
        return cocotb.triggers.Join(self)

    def has_started(self) -> bool:
        """Return ``True`` if the Task has started executing."""
        return self._started

    def cancel(self, msg: typing.Optional[str] = None) -> None:
        """Cancel a Task's further execution.

        When a Task is cancelled, a :exc:`asyncio.CancelledError` is thrown into the Task.
        """
        self._cancelled = CancelledError(msg)
        warnings.warn(
            "Calling this method will cause a CancelledError to be thrown in the "
            "Task sometime in the future.",
            FutureWarning,
            stacklevel=2,
        )
        self.kill()

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

    def exception(self) -> typing.Optional[BaseException]:
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
        elif isinstance(self._outcome, outcomes.Error):
            return self._outcome.error
        else:
            return None

    def __bool__(self) -> bool:
        """``True`` if Task is not done.

        .. deprecated:: 1.7.0
        """
        warnings.warn(
            "Deprecated in favor of the done() method. "
            "Replace with `not task.done()`.",
            DeprecationWarning,
            stacklevel=2,
        )
        return not self.done()

    def __await__(self) -> typing.Generator[typing.Any, typing.Any, T]:
        # It's tempting to use `return (yield from self._coro)` here,
        # which bypasses the scheduler. Unfortunately, this means that
        # we can't keep track of the result or state of the coroutine,
        # things which we expose in our public API. If you want the
        # efficiency of bypassing the scheduler, remove the `@coroutine`
        # decorator from your `async` functions.

        # Hand the coroutine back to the scheduler trampoline.
        return (yield self)


class _RunningCoroutine(Task[T]):
    """
    The result of calling a :any:`cocotb.coroutine` decorated coroutine.

    All this class does is provide some extra attributes.

    .. versionchanged:: 1.8.0
        Moved to the ``cocotb.task`` module.
    """

    def __init__(self, inst, parent):
        super().__init__(inst)
        self._parent = parent
        self.__doc__ = parent._func.__doc__
        self.module = parent._func.__module__
        self.funcname = parent._func.__name__


class _RunningTest(_RunningCoroutine[T]):
    """
    The result of calling a :class:`cocotb.test` decorated object.

    All this class does is change ``__name__`` to show "Test" instead of "Task".

    .. versionchanged:: 1.8.0
        Moved to the ``cocotb.task`` module.
    """

    _name: str = "Test"

    def __init__(self, inst, parent):
        super().__init__(inst, parent)
        self.__name__ = f"{type(self)._name} {self.funcname}"
        self.__qualname__ = self.__name__
