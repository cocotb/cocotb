# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""TaskManager and related code."""

from __future__ import annotations

import sys
from asyncio import CancelledError
from bdb import BdbQuit
from types import CoroutineType
from typing import TYPE_CHECKING, Any, TypeVar

import cocotb
from cocotb._base_triggers import NullTrigger
from cocotb.task import Task, current_task
from cocotb.triggers import Event, Trigger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from exceptiongroup import BaseExceptionGroup


T = TypeVar("T")


async def _waiter(aw: Awaitable[T]) -> T:
    return await aw


class TaskManager:
    r"""An :term:`asynchronous context manager` which enables the user to run :term:`coroutine function`\ s or :keyword:`await` :term:`awaitable`\ s concurrently and wait for them all to finish.

    See :ref:`task_manager_tutorial` for usage information.

    Args:
        continue_on_error: If ``False``, when a child Task fails, all other child Tasks are cancelled.
            If ``True``, other child Tasks are allowed to continue running.
    """

    def __init__(self, continue_on_error: bool = False) -> None:
        self._continue_on_error = continue_on_error

        self._exceptions: set[BaseException] = set()
        self._remaining_tasks: dict[Task[Any], None] = {}
        self._none_remaining = Event()
        self._cancelled: bool = False
        self._finishing: bool = False
        self._entered: bool = False
        # parent task will not exist if we aren't using this as a context manager
        self._parent_task: Task[Any] | None = None

        # Start with no remaining tasks
        self._none_remaining.set()

    def start_soon(self, aw: Awaitable[T], *, name: str | None = None) -> Task[T]:
        """Await the *aw* argument concurrently.

        Args:
            aw: A :class:`~collections.abc.Awaitable` to :keyword:`await` concurrently.
            name: A name to associate with the :class:`!Task` awaiting *aw*.

        Returns:
            A :class:`~cocotb.task.Task` which is awaiting *aw* concurrently.
        """
        coro = aw if isinstance(aw, CoroutineType) else _waiter(aw)
        return self._start_soon(coro, name=name)

    def _start_soon(
        self, coro: Coroutine[Trigger, None, T], *, name: str | None = None
    ) -> Task[T]:
        if self._cancelled:
            raise RuntimeError("Cannot add new Tasks to TaskManager after error")
        elif self._finishing:
            raise RuntimeError("Cannot add new Tasks to TaskManager after finishing")
        elif not self._entered:
            raise RuntimeError(
                "Cannot add new Tasks to TaskManager before entering context"
            )
        if current_task() is not self._parent_task:
            raise RuntimeError("Cannot add new Tasks to TaskManager from another Task")

        task = Task[Any](coro, name=name)
        task._add_done_callback(self._done_callback)
        self._remaining_tasks[task] = None
        self._none_remaining.clear()
        cocotb.start_soon(task)
        return task

    def fork(
        self,
        coro: Callable[[], Coroutine[Trigger, None, T]],
    ) -> Task[T]:
        """Decorate a coroutine function to run it concurrently.

        Args:
            coro: A :term:`coroutine function` to run concurrently.

        Returns:
            A :class:`~cocotb.task.Task` which is running *coro* concurrently.

        .. code-block:: python

            async with TaskManager() as tm:

                @tm.fork
                async def my_func():
                    # Do stuff
                    ...

                @tm.fork
                async def other_func():
                    # Do other stuff in parallel to my_func
                    ...
        """
        return self._start_soon(coro(), name=coro.__name__)

    def _done_callback(self, task: Task[Any]) -> None:
        """Callback run when a child Task finishes."""
        del self._remaining_tasks[task]
        if not self._remaining_tasks:
            self._none_remaining.set()

        # If a child Task failed, cancel all other child Tasks.
        if not task.cancelled() and (exc := task.exception()) is not None:
            self._exceptions.add(exc)
            if not self._continue_on_error:
                self._cancel()

    def _cancel(self) -> None:
        """Cancel all unfinished child Tasks."""
        if self._cancelled:
            return
        self._cancelled = True

        # If a child Task fails while we are in the middle of a TaskManager block,
        # cancel the parent Task to force the block to end.
        if not self._finishing and self._parent_task is not None:
            self._parent_task.cancel()

        # Cancel all child Tasks.
        for task in self._remaining_tasks:
            task.cancel()

    async def __aenter__(self) -> Self:
        if self._finishing:
            raise RuntimeError("Cannot re-enter finished TaskManager context")
        self._entered = True
        self._parent_task = current_task()
        return self

    async def __aexit__(
        self, exc_type: object, exc: BaseException | None, traceback: object
    ) -> None:
        self._finishing = True

        if self._parent_task is not None and self._cancelled:
            # The context block was cancelled due to a child Task failure.
            if isinstance(exc, CancelledError):
                # Suppress CancelledError in this case to allow child Tasks to finish cancelling.
                exc = None
                assert self._parent_task is not None
                self._parent_task._uncancel()
            else:
                # The context block ignored the cancellation. Hard fail the test.
                # There is a special case in Task if a cancelled Task finishes without
                # raising CancelledError, it fails the test. So we just await *something*
                # here to hit that code path.
                # TODO Make this force a test failure.
                self._cancel()
                await NullTrigger()
        elif exc is not None:
            if isinstance(exc, CancelledError):
                # Something else cancelled the parent task. Propagate CancelledError.
                self._cancel()
                return None  # re-raise CancelledError
            elif isinstance(exc, (KeyboardInterrupt, SystemExit, BdbQuit)):
                # Certain BaseExceptions should be immediately propagated like they are in Task.
                self._cancel()
                return None  # re-raise exception
            else:
                # Block finished with an exception.
                self._cancel()

        # Wait for all Tasks to finish / finish cancelling.
        try:
            await self._none_remaining.wait()
        except CancelledError:
            # Cancel all child Tasks if the current Task is cancelled by the user while
            # waiting for all child Tasks to finish. If the TaskManager is already
            # cancelling due to a child Task failure, this will no-op.
            self._cancel()
            raise
        except BaseException:
            # The current Task failed while waiting for child Tasks to finish.
            # This is likely because we ignored a CancelledError since there is no other
            # way to fail this await AFAICT. Cancel children and let it pass up as there's
            # nothing we can do.
            # TODO Make this force a test failure.
            self._cancel()
            raise

        self._finished = True

        # Build BaseExceptionGroup if there were any errors. Ignore CancelledError.
        if exc is not None and not isinstance(exc, CancelledError):
            self._exceptions.add(exc)
        if self._exceptions:
            # BaseExceptionGroup constructor will automatically return an ExceptionGroup if all elements are Exceptions.
            raise BaseExceptionGroup(
                "TaskManager finished with errors", tuple(self._exceptions)
            )

        # Return True to handle suppressing CancelledError if there were no exceptions
        return True  # type: ignore[return-value]  # __aexit__ can return True
