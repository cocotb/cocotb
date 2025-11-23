"""TaskManager and related code."""

from __future__ import annotations

import sys
from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, TypeVar

import cocotb
from cocotb.task import Task, current_task
from cocotb.triggers import Event, Trigger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Coroutine

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from exceptiongroup import BaseExceptionGroup

if sys.version_info >= (3, 10):
    from typing import ParamSpec

    P = ParamSpec("P")


T = TypeVar("T")


async def _waiter(aw: Awaitable[T]) -> T:
    return await aw


class TaskManager:
    r"""An :term:`asynchronous context manager` which enables the user to run :term:`coroutine function`\ s or :keyword:`await` :term:`awaitable`\ s concurrently and wait for them all to finish.

    :term:`!awaitables` can be added to the :class:`!TaskManager` using :meth:`start_soon`.
    Likewise, :meth:`fork` can be used to add :term:`coroutine function`\ s.
    Both methods return the :class:`!Task` which is running the concurrent behavior.

    When control reaches the end of the context block
    the :class:`!TaskManager` blocks the :class:`!Task` using it until all children :class:`!Task`\ s of the :class:`!TaskManager` complete.

    .. code-block:: python

        async with TaskManager() as tm:

            @tm.fork
            async def drive_if1(): ...

            @tm.fork
            async def drive_if2(): ...

        # Control returns here when all drive Tasks have completed

    TODO What happens when a child Task fails

    TODO What happens when the TaskManager body fails

    TODO TaskManagers can be nested

    TODO directly calling start_soon() and add()

    TODO directly interacting with result Task objects
    """

    def __init__(self) -> None:
        self._tasks: list[Task[Any]] = []
        self._parent_task: Task[Any]
        self._in_exit: bool = False
        self._cancelling: bool = False

    def _done_callback(self, task: Task[Any]) -> None:
        if not task.cancelled() and task.exception() is not None:
            self._cancel()

    def _cancel(self) -> None:
        """Cancel all unfinished child :class:`!Tasks`."""
        if self._cancelling:
            return
        self._cancelling = True

        # If a child Task fails while we are in the middle of a TaskManager block,
        # cancel the parent Task to force the block to end.
        if not self._in_exit:
            # We can't use `_parent_task.cancel()` because that requires the Task to
            # fully cancel or else cause a RuntimeError, but we only want the
            # cancellation to propagate up to the TaskManager.
            self._parent_task._soft_cancel()

        # Cancel all child Tasks.
        for task in self._tasks:
            task.cancel()

    def start_soon(self, aw: Awaitable[T], *, name: str | None = None) -> Task[T]:
        """Awaits its argument concurrently to other calls to this function.

        Args:
            aw: A :class:`~collections.abc.Awaitable` to :keyword:`await` concurrently.
            name: A name to associate with the :class:`!Task` awaiting *aw*.

        Returns:
            A :class:`~cocotb.task.Task` which is awaiting *aw* concurrently.
        """
        if self._cancelling:
            raise RuntimeError(
                "Cannot add new Tasks to TaskManager that is cancelled"
            ) from None
        task = Task[Any](_waiter(aw), name=name)
        task._add_done_callback(self._done_callback)
        self._tasks.append(task)
        cocotb.start_soon(task)
        return task

    def fork(
        self,
        coro: Callable[P, Coroutine[Trigger, None, T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Task[T]:
        """Decorate a coroutine function to run it concurrently.

        Args:
            coro: A :term:`coroutine function` to run concurrently.
            args: Positional args to pass to the call of *coro*.
            kwargs: Keyword args to pass to the call of *coro*.

        Returns:
            A :class:`~cocotb.task.Task` which is running *coro* concurrently.

        .. code-block:: python

            async with TaskManager() as tm:

                @tm.fork
                async def my_func():
                    # Do stuff
                    ...

                @tb.fork
                async def other_func():
                    # Do other stuff in parallel to my_func
                    ...
        """
        return self.start_soon(coro(*args, **kwargs), name=coro.__name__)

    async def __aenter__(self) -> Self:
        self._parent_task = current_task()
        return self

    async def __aexit__(
        self, exc_type: object, exc_value: BaseException | None, traceback: object
    ) -> None:
        self._in_exit = True
        if exc_value is not None:
            self._cancel()

        remaining = {task for task in self._tasks if not task.done()}

        # Wait for all Tasks to finish / finish cancelling.
        if remaining:
            done = Event()

            def on_done(task: Task[Any]) -> None:
                remaining.remove(task)
                if not remaining:
                    done.set()

            for task in remaining:
                task._add_done_callback(on_done)

            try:
                await done.wait()
            except CancelledError:
                self._cancel()
                raise

        # Build BaseExceptionGroup if there are any errors.
        errors = []
        if exc_value is not None and not isinstance(exc_value, CancelledError):
            errors.append(exc_value)
        errors.extend(
            exc
            for task in self._tasks
            if not task.cancelled() and (exc := task.exception()) is not None
        )
        if errors:
            raise BaseExceptionGroup("TaskManager finished with errors", errors)
