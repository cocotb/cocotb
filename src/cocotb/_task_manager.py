# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""TaskManager and related code."""

from __future__ import annotations

import sys
from asyncio import CancelledError
from bdb import BdbQuit
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, overload

from cocotb.task import Task, current_task
from cocotb.triggers import Event, NullTrigger

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from exceptiongroup import BaseExceptionGroup

if sys.version_info >= (3, 10):
    from typing import ParamSpec

    P = ParamSpec("P")


T = TypeVar("T")


class TaskManager:
    r"""An :term:`asynchronous context manager` which runs :term:`coroutine function`\ s or :term:`awaitable`\ s concurrently until all finish.

    See :ref:`task_manager_tutorial` for detailed usage information.

    Args:
        default_continue_on_error: Default value for *continue_on_error* for child Tasks started by this TaskManager.
        context_continue_on_error: Value for *continue_on_error* for the context block itself.

            If not specified, defaults to the value of *default_continue_on_error*.

    .. versionadded:: 2.1
    """

    def __init__(
        self,
        *,
        default_continue_on_error: bool = False,
        context_continue_on_error: bool | None = None,
    ) -> None:
        self._default_continue_on_error = default_continue_on_error
        self._context_continue_on_error: bool = (
            context_continue_on_error
            if context_continue_on_error is not None
            else default_continue_on_error
        )

        # We don't keep all children Tasks around, just the ones that haven't finished yet,
        # so we have to save the exceptions for the ExceptionGroup we raise at the end of the context block.
        self._exceptions: set[BaseException] = set()
        # dict value is per-Task continue_on_error setting
        self._remaining_tasks: dict[Task[Any], bool] = {}
        self._none_remaining = Event()
        # Children were cancelled due to a child Task/block failure.
        self._cancelled: bool = False
        # We started __aexit__. Ensures we dont add more Tasks after the context block has started finishing.
        self._finishing: bool = False
        # For protecting against adding Tasks before entering the context block
        self._entered: bool = False
        # The parent Task which entered the context block.
        # Used to ensure only the parent Task can add child Tasks,
        # and to cancel the parent Task if a child Task fails while the block is still running.
        self._parent_task: Task[Any]

        # Start with no remaining tasks
        self._none_remaining.set()

    def start_soon(
        self,
        aw: Awaitable[T],
        *,
        name: str | None = None,
        continue_on_error: bool | None = None,
    ) -> Task[T]:
        r"""Await the *aw* argument concurrently.

        Args:
            aw: A :class:`~collections.abc.Awaitable` to :keyword:`await` concurrently.
            name: A name to associate with the :class:`!Task` awaiting *aw*.
            continue_on_error: Value of *continue_on_error* for this Task only.

                If not specified, defaults to the value of the :class:`!TaskManager`'s *default_continue_on_error* argument.

        Returns:
            A :class:`~cocotb.task.Task` which is awaiting *aw* concurrently.
        """
        # Ensure that we can add a new Task to this TaskManager before creating the Task.
        # We would have to close it if it failed.
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

        # Create the Task and tie it to this TaskManager via the done callback.
        task = Task[T](aw, name=name)
        task._add_done_callback(self._done_callback)
        # Track the Task and store per-Task continue_on_error setting
        self._remaining_tasks[task] = (
            continue_on_error
            if continue_on_error is not None
            else self._default_continue_on_error
        )
        self._none_remaining.clear()
        # Start the Task to running.
        task.start_soon()
        return task

    @overload
    def fork(
        self,
        coro_func: Callable[[], Awaitable[T]],
        /,
    ) -> Task[T]: ...

    @overload
    def fork(
        self, *, continue_on_error: bool
    ) -> Callable[[Callable[[], Awaitable[T]]], Task[T]]: ...

    def fork(
        self,
        coro_func: Callable[..., Awaitable[T]] | None = None,
        *,
        continue_on_error: bool | None = None,
    ) -> Task[T] | Callable[[Callable[[], Awaitable[T]]], Task[T]]:
        r"""Decorate a coroutine function to run it concurrently.

        .. note::
            This does not necessarily have to be a coroutine function.
            Any callable which returns a :class:`~collections.abc.Awaitable` can be used.

        Args:
            coro_func: A :term:`coroutine function` to run concurrently. Typically this is the decorated function.
            continue_on_error: Value of *continue_on_error* for this Task only.

                If not specified, defaults to the value of the :class:`!TaskManager`'s *default_continue_on_error* argument.
                Passing this requires calling the :meth:`fork` method before decorating the coroutine function.

        Returns:
            A :class:`~cocotb.task.Task` which is running *coro_func* concurrently.

        .. code-block:: python

            async with TaskManager() as tm:

                @tm.fork
                async def my_func():
                    # Do stuff
                    ...

                @tm.fork(continue_on_error=True)
                async def other_func():
                    # Do other stuff in parallel to my_func
                    ...
        """
        # Handle the case where fork is called as a function and returns the decorator.
        if coro_func is None:
            if continue_on_error is None:
                raise TypeError(
                    "Missing required keyword-only argument: 'continue_on_error'"
                )

            def deco(
                coro: Callable[[], Awaitable[T]],
            ) -> Task[T]:
                return self.fork(  # type: ignore[call-overload]
                    coro,
                    continue_on_error=continue_on_error,
                )

            return deco

        return self.start_soon(
            coro_func(), name=coro_func.__name__, continue_on_error=continue_on_error
        )

    def _done_callback(self, task: Task[Any]) -> None:
        """Callback run when a child Task finishes."""
        continue_on_error = self._remaining_tasks.pop(task)
        if not self._remaining_tasks:
            self._none_remaining.set()

        # If a child Task failed, cancel all other child Tasks.
        if not task.cancelled() and (exc := task.exception()) is not None:
            self._exceptions.add(exc)
            if not continue_on_error:
                self._cancel()

    def _cancel(self) -> None:
        """Cancel all unfinished child Tasks."""
        if self._cancelled:
            return
        self._cancelled = True

        # If a child Task fails while we are in the middle of a TaskManager block,
        # cancel the parent Task to force the block to end.
        if not self._finishing:
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

        # Propagate special exceptions immediately.
        # The GeneratorExit case is there so if the block is cancelled due to a child Task failure,
        # and the block squashes the CancelledError and does an await, a GeneratorExit is thrown at the await, which may end up here.
        if isinstance(exc, (KeyboardInterrupt, SystemExit, BdbQuit, GeneratorExit)):
            self._cancel()
            return None  # re-raise exception

        if self._cancelled:
            # The context block was cancelled due to a child Task failure.
            if isinstance(exc, CancelledError):
                # Suppress CancelledError in this case to allow child Tasks to finish cancelling.
                exc = None
                self._parent_task._uncancel()
            else:
                # The context block ignored the cancellation and either threw some other exception or finished successfully.
                # We await a token NullTrigger to allow the parent Task to kill the Task due to ignored CancelledError.
                await NullTrigger()
                # This will never run as a GeneratorExit will be thrown at the above await.
                return None  # pragma: no cover
        elif exc is not None:
            if isinstance(exc, CancelledError):
                # Something else cancelled the parent task. Propagate CancelledError immediately.
                self._cancel()
                return None  # re-raise CancelledError
            elif not self._context_continue_on_error:
                # Block finished with an exception and we are not continuing on error.
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
            self._cancel()
            raise

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
