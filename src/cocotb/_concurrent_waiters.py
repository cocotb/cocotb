# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import sys
from asyncio import CancelledError
from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

import cocotb
from cocotb.task import Task
from cocotb.triggers import Event

if TYPE_CHECKING:
    from collections.abc import Awaitable

if sys.version_info >= (3, 10):
    from typing import TypeAlias

ReturnWhenType: TypeAlias = Literal[
    "FIRST_COMPLETED", "FIRST_EXCEPTION", "ALL_COMPLETED"
]

T = TypeVar("T")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")


@overload
async def wait(
    a: Awaitable[T],
    /,
    *,
    return_when: ReturnWhenType,
) -> tuple[Task[T]]: ...


@overload
async def wait(
    a: Awaitable[T],
    b: Awaitable[T2],
    /,
    *,
    return_when: ReturnWhenType,
) -> tuple[Task[T], Task[T2]]: ...


@overload
async def wait(
    a: Awaitable[T],
    b: Awaitable[T2],
    c: Awaitable[T3],
    /,
    *,
    return_when: ReturnWhenType,
) -> tuple[Task[T], Task[T2], Task[T3]]: ...


@overload
async def wait(
    a: Awaitable[T],
    b: Awaitable[T2],
    c: Awaitable[T3],
    d: Awaitable[T4],
    /,
    *,
    return_when: ReturnWhenType,
) -> tuple[Task[T], Task[T2], Task[T3], Task[T4]]: ...


@overload
async def wait(
    *aw: Awaitable[T], return_when: ReturnWhenType
) -> tuple[Task[T], ...]: ...


async def wait(
    *awaitables: Awaitable[Any], return_when: ReturnWhenType
) -> tuple[Task[Any], ...]:
    r"""Await on all given *awaitables* concurrently and block until the *return_when* condition is met.

    Every :class:`~collections.abc.Awaitable` given to the function is :keyword:`await`\ ed concurrently in its own :class:`~cocotb.task.Task`.
    When the return conditions specified by *return_when* are met, this function returns those :class:`!Task`\ s.
    Once the return conditions are met, any waiter tasks which are still running are cancelled.
    This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments, only the waiter tasks.

    The *return_when* condition must be one of the following:

    - ``"FIRST_COMPLETED"``: Returns after the first of the *awaitables* completes, regardless if that was due to an exception or not.
    - ``"FIRST_EXCEPTION"``: Returns after all *awaitables* complete or after the first *awaitable* that completes due to an exception.
    - ``"ALL_COMPLETED"``: Returns after all *awaitables* complete.

    Args:
        awaitables: The :class:`Awaitable`\ s to concurrently :keyword:`!await` upon.
        return_when:
            The condition that must be met before returning.
            One of ``"FIRST_COMPLETED"``, ``"FIRST_EXCEPTION"``, or ``"ALL_COMPLETED"``.

    Returns:
        A tuple of waiter :class:`~cocotb.task.Task`\ s.
        The order of the return tuple corresponds to the order of the input.
    """

    async def waiter(aw: Awaitable[T]) -> T:
        return await aw

    tasks = tuple(Task[Any](waiter(a)) for a in awaitables)

    # Event which is set by done_callback when return condition is met.
    done = Event()

    # order of cancellation may matter, so we use dict(), which is ordered unlike set()
    remaining = dict.fromkeys(tasks)

    # Cancel all remaining tasks.
    # Use a flag to prevent multiple cancellation.
    cancelled: bool = False

    def cancel() -> None:
        nonlocal cancelled
        if cancelled:
            return

        cancelled = True
        for t in remaining:
            t.cancel()

    # Define done_callbacks which set the "done" Event when the return condition is met.
    if return_when == "FIRST_COMPLETED":

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                done.set()
            else:
                # Cancel remaining before they have a chance to resume.
                cancel()

    elif return_when == "FIRST_EXCEPTION":

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                done.set()
            elif not task.cancelled() and task.exception() is not None:
                # Cancel remaining before they have a chance to resume.
                cancel()

    else:

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                done.set()

    # Register done_callback to all waiter tasks.
    for task in tasks:
        task._add_done_callback(done_callback)
        cocotb.start_soon(task)

    try:
        await done.wait()
    except CancelledError:
        # Cancel waiter tasks if this coroutine was cancelled.
        for task in tasks:
            task.cancel()
        raise

    return tasks


@overload
async def select(
    *awaitables: Awaitable[T], return_exception: Literal[False] = False
) -> tuple[int, T]: ...


@overload
async def select(
    *awaitables: Awaitable[T], return_exception: Literal[True]
) -> tuple[int, T | BaseException]: ...


async def select(
    *awaitables: Awaitable[T], return_exception: bool = False
) -> tuple[int, T | BaseException]:
    r"""Await on all given *awaitables* concurrently and return the index and result of the first to complete.

    After the first *awaitable* completes, the remaining waiter tasks are cancelled.
    This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments,
    only the internal waiter tasks.

    Args:
        awaitables: The :class:`~cocotb.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.
        return_exception:
            If ``False`` (default), re-raises the exception when an *awaitable* results in an exception.
            If ``True``, returns the exception rather than re-raising when an *awaitable* results in an exception.

    Returns:
        A tuple comprised of the index into the argument list (0-based) of the first *awaitable* to complete, and the *awaitable*'s result.

    Raises:
        ValueError: If no *awaitables* are provided.
    """
    if len(awaitables) == 0:
        raise ValueError("At least one awaitable required")

    tasks = await wait(*awaitables, return_when="FIRST_COMPLETED")

    # Find which awaitable completed.
    idx: int
    for i, task in enumerate(tasks):
        if task.done() and not task.cancelled():
            idx = i
            break
    else:  # pragma: no cover
        raise RuntimeError("Reached unreachable code section")

    if return_exception and (exc := task.exception()) is not None:
        return idx, exc
    else:
        return idx, task.result()


@overload
async def gather(
    a: Awaitable[T],
    /,
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[T]: ...


@overload
async def gather(
    a: Awaitable[T],
    b: Awaitable[T2],
    /,
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[T, T2]: ...


@overload
async def gather(
    a: Awaitable[T],
    b: Awaitable[T2],
    c: Awaitable[T3],
    /,
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[T, T2, T3]: ...


@overload
async def gather(
    a: Awaitable[T],
    b: Awaitable[T2],
    c: Awaitable[T3],
    d: Awaitable[T4],
    /,
    *,
    return_exceptions: Literal[False] = False,
) -> tuple[T, T2, T3, T4]: ...


@overload
async def gather(
    *aw: Awaitable[T], return_exceptions: Literal[False] = False
) -> tuple[T, ...]: ...


@overload
async def gather(
    *aw: Awaitable[T], return_exceptions: Literal[True]
) -> tuple[T | BaseException, ...]: ...


async def gather(
    *awaitables: Awaitable[Any],
    return_exceptions: bool = False,
) -> tuple[Any, ...]:
    r"""Await on all given *awaitables* concurrently and return their results once all have completed.

    After the return condition, based on *return_exceptions*, is met, the remaining waiter tasks are cancelled.
    This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments,
    only the internal waiter tasks.

    Args:
        awaitables: The :class:`~collection.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.
        return_exceptions:
            If ``False`` (default), after the first *awaitable* results in an exception, cancels the remaining *awaitables* and re-raises the exception.
            If ``True``, returns the exception rather than the result value when an *awaitable* results in an exception.

    Returns:
        A tuple of the results of awaiting each *awaitable* in the same order they were given.
        The order of the return tuple corresponds to the order of the input.
    """
    if len(awaitables) == 0:
        return ()

    tasks = await wait(
        *awaitables,
        return_when="ALL_COMPLETED" if return_exceptions else "FIRST_EXCEPTION",
    )
    if return_exceptions:
        # We now know there were no cancelled Tasks, so get all exceptions or results.
        return tuple(
            exc if (exc := task.exception()) is not None else task.result()
            for task in tasks
        )
    else:
        # Find first error if there is one.
        for task in tasks:
            if not task.cancelled() and (exc := task.exception()) is not None:
                raise exc
        # We now know there were no cancelled Tasks and no exceptions, so get all results.
        return tuple(task.result() for task in tasks)
