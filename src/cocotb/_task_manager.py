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
from cocotb.triggers import Event

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

    See :ref:`task-manager-tutorial` for detailed usage information.

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
        task._start_soon()
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
        self, exc_type: object, body_exc: BaseException | None, traceback: object
    ) -> None:
        self._finishing = True

        # Propagate special exceptions immediately after best-effort child cancellation.
        # The GeneratorExit case is there so if the block is cancelled due to a child Task failure,
        # and the block squashes the CancelledError and does an await, a GeneratorExit is thrown at the await, which may end up here.
        if isinstance(
            body_exc, (KeyboardInterrupt, SystemExit, BdbQuit, GeneratorExit)
        ):
            self._cancel()
            return None  # re-raise exception

        external_cancellation: CancelledError | None = None

        if self._cancelled:
            # The context block was cancelled due to a child Task failure.
            if isinstance(body_exc, CancelledError):
                # Suppress CancelledError in this case to allow child Tasks to finish cancelling.
                self._parent_task._uncancel()
            else:
                # The context block ignored the cancellation and either threw some other exception or finished successfully.
                # We have to have this here as we are basically treating the body as a separate Task,
                # but we can't use the logic in Task, so we have to repeat it here.
                self._exceptions.add(
                    RuntimeError("TaskManager context block ignored cancellation")
                )
        elif body_exc is not None:
            if isinstance(body_exc, CancelledError):
                # We don't record CancelledErrors in the exceptions set.
                # Just as if it were a child Task, we cancel all children when one fails.
                # We unconditionally cancel here as context block cancellation really means the parent was externally cancelled.
                external_cancellation = body_exc
                self._cancel()
            else:
                # The context block raised an exception.
                # Just as if it were a child Task, we record the exception and cancel the other children if not continue_on_error.
                self._exceptions.add(body_exc)
                if not self._context_continue_on_error:
                    self._cancel()
        else:
            # The context block finished successfully without something else causing a cancellation.
            pass  # pragma: no cover  # empty branches are optimized out by the interpreter

        # Wait for all Tasks to finish / finish cancelling.
        while not self._none_remaining.is_set():
            try:
                await self._none_remaining.wait()
            except CancelledError as exc:
                # Got an external cancellation while waiting for all child Tasks to finish.
                # If the TaskManager is already cancelling due to a child Task failure, this will no-op.
                # If we get a cancellation after another cancellation while wait, this will also no-op.
                external_cancellation = exc
                self._cancel()
            except BaseException:
                # Something horrible has happened, cancel children as a best-effort and immediately propagate the exception.
                self._cancel()
                raise

        # We have to propagate the external cancellation if it occurred either in the context block
        # (task was externally cancelled while in the block), or while waiting for all child Tasks to finish.
        # The assumption is that if someone called `parent_task.cancel()`, the CancelledError must be propagated
        # to the caller after all children have finished.
        # We don't have to worry about CancelledErrors from child Tasks here, as no one should be able to get a reference to them.
        # (Well... current_task() could allow someone to do something convoluted.)
        if external_cancellation:
            raise external_cancellation from None

        if self._exceptions:
            # BaseExceptionGroup constructor will automatically return an ExceptionGroup if all elements are Exceptions.
            raise BaseExceptionGroup(
                "TaskManager finished with errors", tuple(self._exceptions)
            )

        # Return True to handle suppressing CancelledError if there were no exceptions
        return True  # type: ignore[return-value]  # __aexit__ can return True
