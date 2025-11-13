# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""TaskManager and related code."""

from __future__ import annotations

import sys
from asyncio import CancelledError
from bdb import BdbQuit
from types import CoroutineType
from typing import TYPE_CHECKING, Any, Literal, TypeVar

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

    The :deco:`fork` decorator can be used to run :term:`coroutine function`\ s in parallel as children of the :class:`!TaskManager` object.
    When control reaches the end of the context block
    the :class:`!TaskManager` blocks the calling :class:`!Task` until all children :class:`!Task`\ s complete.

    .. code-block:: python

        async with TaskManager() as tm:

            @tm.fork
            async def drive_interface1(): ...

            @tm.fork
            async def drive_interface2(): ...

        # Control returns here when all drive Tasks have completed

    After exiting the context block,
    if any child :class:`!Task` failed with an exception,
    one of two behaviors will occur:
    if the *continue_on_error* parameter is ``False`` (default), all other child :class:`!Task`\ s are cancelled;
    if the *continue_on_error* parameter is ``True``, other child :class:`!Task`\ s are allowed to continue running.

    After all child :class:`!Task`\ s have finished,
    all exceptions, besides :exc:`CancelledError`, are gathered into an :exc:`ExceptionGroup`,
    or a :exc:`BaseExceptionGroup`, if at least one of the exceptions is a :exc:`BaseException`,
    and raised in the enclosing scope.

    You can catch the :exc:`!ExceptionGroup` to handle errors from child :class:`!Task`\ s
    by either catching the :exc:`!ExceptionGroup` as you would typically;
    or, if you are running Python 3.11 or later,
    using the new ``except*`` syntax to catch specific exception types from the group.
    This new syntax will run the except clause for each matching exception in the group.

    .. code-block:: python

        try:
            async with TaskManager() as tm:

                @tm.fork
                async def task1():
                    ...
                    raise ValueError("An error occurred in task1")

                @tm.fork
                async def task2():
                    ...
                    raise ValueError("An error occurred in task2")

        except* ValueError as e:
            # This will print both ValueErrors from task1 and task2
            cocotb.log.info(f"Caught ValueError from TaskManager: {e}")

    You are permitted to add any :keyword:`await` statement to the body of the context block.
    This means that it is possible for child tasks to start running, and fail, before the context block is exited.
    In this case, the context block will also exit with a :exc:`CancelledError` if the *continue_on_error* parameter is ``False`` (default),
    or continue if *continue_on_error* is ``True``.

    .. code-block:: python

        e = Event()

        async with TaskManager() as tm:

            @tm.fork
            async def task1():
                raise ValueError("An error occurred in task1")

            try:
                await e.wait()  # During this await, task1 will fail
            except CancelledError:
                cocotb.log.info(
                    "The rest of the context block will be skipped due to task1 failing"
                )
                raise  # DON'T FORGET THIS

            ...  # This code will be skipped


    In addition to the :deco:`!fork` method for starting :term:`coroutine function`\ s concurrently,
    :meth:`start_soon` is also provided for :keyword:`await`\ ing arbitrary :term:`awaitable`\ s concurrently.

    .. code-block:: python

        async with TaskManager() as tm:
            tm.start_soon(RisingEdge(cocotb.top.operation_complete))

            @tm.fork
            async def watchdog():
                await Timer(1, "us")
                raise TimeoutError("Operation did not complete in time")

    You can inspect the result of child classes by storing the :class:`!Task` objects returned by :meth:`start_soon` method.
    When decoratoring a :term:`coroutine function` with :deco:`!fork`,
    the name of the function will become the returned :class:`!Task` object.

    .. code-block:: python

        async with TaskManager() as tm:
            task1 = tm.start_soon(RisingEdge(cocotb.top.signal_a))

            @tm.fork
            async def task2():
                return 42


        assert task1.done()
        assert task1.result() is RisingEdge(cocotb.top.signal_a)

        assert task2.done()
        assert task2.result() == 42

    After exiting the context block and waiting for all child :class:`!Task`\ s to complete,
    or :keyword:`await`\ ing the :class:`!TaskManager` instance the first time,
    no further calls to :meth:`start_soon` or :deco:`!fork` are permitted;
    attempting to do so will raise a :exc:`RuntimeError`.

    Additionally, after a child :class:`!Task` fails and the :class:`!TaskManager` begins cancelling other child :class:`!Task`\ s,
    no further calls to :meth:`start_soon` or :deco:`!fork` are permitted;
    attempting to do so will raise a :exc:`RuntimeError`,
    unless the *continue_on_error* parameter is ``True`` and the context block has not yet exited.

    .. code-block:: python

        try:
            async with TaskManager(continue_on_error=True) as tm:

                @tm.fork
                async def task1():
                    raise ValueError("An error occurred in task1")

                await Timer(1)
                # At this point task1 has already failed, but because continue_on_error=True,
                # we can still add new tasks.

                @tm.fork
                async def task2(): ...

        except* ValueError as e:
            cocotb.log.info(f"Caught ValueError from task1: {e}")
            pass

        assert task2.done()  # task2 was able to run to completion

    And of course, :class:`!TaskManager` can be arbitrarily nested.
    When any child :class:`!Task` fails, the entire tree of child :class:`!Task`\ s will eventually be cancelled.

    .. code-block:: python
        async with TaskManager() as tm_outer:

            @tm_outer.fork
            async def outer_task():
                async with TaskManager() as tm_inner:

                    @tm_inner.fork
                    async def inner_task(): ...

            async with TaskManager() as tm_another:

                @tm_another.fork
                async def another_task(): ...

    .. warning::
        Just like with :class:`~cocotb.task.Task`, cancelling a :class:`!TaskManager` instance
        (after a child fails, or if another Task cancels the Task using the :class:`!TaskManager`)
        and squashing the resulting :exc:`CancelledError` will cause the test to fail immediately.
        Always remember to re-raise the :exc:`!CancelledError` if you catch it.

    Args:
        continue_on_error: If ``False``, when a child Task fails, all other child Tasks are cancelled.
            If ``True``, other child Tasks are allowed to continue running.

    """

    def __init__(self, continue_on_error: bool = False) -> None:
        self._continue_on_error = continue_on_error

        self._exceptions: list[BaseException] = []
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
        """Await the *aw* argument concurrently to other calls to this method.

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

                @tb.fork
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
            self._exceptions.append(exc)
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
            self._exceptions.append(exc)
        if self._exceptions:
            # BaseExceptionGroup constructor will automatically return an ExceptionGroup if all elements are Exceptions.
            raise BaseExceptionGroup(
                "TaskManager finished with errors", self._exceptions
            )

        # Return True to handle suppressing CancelledError if there were no exceptions
        return True  # type: ignore[return-value]  # __aexit__ can return True

    async def _finish_(self, exc: BaseException | None = None) -> None | Literal[True]:
        """Wait for all child Tasks to finish and handle errors."""
