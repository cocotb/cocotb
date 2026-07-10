# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import sys
from collections.abc import Awaitable, Iterable
from typing import TYPE_CHECKING, Any, Callable, Literal, TypeVar, overload

from cocotb._base_triggers import _InternalEvent
from cocotb.task import Task

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
    a: Awaitable[T], /, *, return_when: ReturnWhenType
) -> tuple[int | None, tuple[Task[T]]]: ...


@overload
async def wait(
    a: Awaitable[T], b: Awaitable[T2], /, *, return_when: ReturnWhenType
) -> tuple[int | None, tuple[Task[T], Task[T2]]]: ...


@overload
async def wait(
    a: Awaitable[T],
    b: Awaitable[T2],
    c: Awaitable[T3],
    /,
    *,
    return_when: ReturnWhenType,
) -> tuple[int | None, tuple[Task[T], Task[T2], Task[T3]]]: ...


@overload
async def wait(
    a: Awaitable[T],
    b: Awaitable[T2],
    c: Awaitable[T3],
    d: Awaitable[T4],
    /,
    *,
    return_when: ReturnWhenType,
) -> tuple[int | None, tuple[Task[T], Task[T2], Task[T3], Task[T4]]]: ...


async def wait(
    *awaitables: Awaitable[Any], return_when: ReturnWhenType
) -> tuple[int | None, tuple[Task[Any], ...]]:
    r"""Await on all given *awaitables* concurrently and block until the *return_when* condition is met.

    Every :class:`~collections.abc.Awaitable` given to the function is :keyword:`await`\ ed concurrently in its own :class:`~cocotb.task.Task`.
    When the return conditions specified by *return_when* are met, this function returns those :class:`!Task`\ s.
    Once the return conditions are met, any waiter tasks which are still running are cancelled.

    .. note::
        This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments,
        only :term:`coroutines <coroutine>`,  :term:`triggers <trigger>`, or other user-defined :term:`!awaitables`.

    The behavior of this function depends on the *return_when* condition:

    - ``"FIRST_COMPLETED"``: Returns after the first of the *awaitables* completes, regardless if that was due to an exception or not.
    - ``"FIRST_EXCEPTION"``: Returns after all *awaitables* complete or after the first *awaitable* that completes due to an exception.
    - ``"ALL_COMPLETED"``: Returns after all *awaitables* complete.

    The index value in the result is the 0-based index into the argument list and has the following meanings, depending on the *return_when* condition:

    - ``"FIRST_COMPLETED"``: The index of the first *awaitable* to complete, regardless of whether it completed successfully or with an exception.
    - ``"FIRST_EXCEPTION"``: The index of the first *awaitable* to complete with an exception, or ``None`` if all completed successfully.
    - ``"ALL_COMPLETED"``: Always ``None``, since all *awaitables* must complete before returning.

    Guarantees:
        This function guarantees that all *awaitables* are cancelled in the event of the cancellation of the caller.
        This function guarantees that all *awaitables* are cancelled after the *return_when* condition is met, if any are still running.
        This function guarantees that in the event of child cancellation, all *awaitables* have finished cancellation before returning to the caller,
        ensuring that any side-effectful clean-up has completed.

    Args:
        awaitables: The :class:`~collections.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.
        return_when:
            The condition that must be met before returning.
            One of ``"FIRST_COMPLETED"``, ``"FIRST_EXCEPTION"``, or ``"ALL_COMPLETED"``.

    Raises:
        ValueError: If no *awaitables* are provided.

    Returns:
        The index into the argument list (0-based) or ``None`` based on meanings described above,
        and a tuple of waiter :class:`~cocotb.task.Task`\ s corresponding to the *awaitables* given as arguments.

    .. versionadded:: 2.1
    """
    if len(awaitables) == 0:
        raise ValueError("At least one awaitable required")

    return await _wait(
        awaitables,
        return_when,
        lambda: f"wait({', '.join(repr(a) for a in awaitables)})",
    )


async def _wait(
    awaitables: Iterable[Awaitable[Any]],
    return_when: ReturnWhenType,
    _repr: Callable[[], str],
) -> tuple[int | None, tuple[Task[Any], ...]]:

    waiters = [Task[Any](a) for a in awaitables]
    # Use dict (insertion-ordered) so cancellation order is deterministic and we have O(1) insertion and removals.
    remaining = dict.fromkeys(waiters)
    # Set when all tasks have completed, regardless of reason.
    complete = _InternalEvent(_repr)
    # The first task to complete, stored regardless of return_when condition.
    first_completed: Task[Any] | None = None
    # Flag to prevent multiple cancellation
    cancelled: bool = False

    def cancel_remaining() -> None:
        nonlocal cancelled
        if cancelled:
            return
        cancelled = True
        for task in remaining:
            task.cancel()

    if return_when == "FIRST_COMPLETED":

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                complete.set()
            nonlocal first_completed
            if first_completed is None:
                first_completed = task
                cancel_remaining()

    elif return_when == "FIRST_EXCEPTION":

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                complete.set()
            nonlocal first_completed
            if first_completed is None and (
                task.cancelled() or task.exception() is not None
            ):
                first_completed = task
                cancel_remaining()

    else:

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                complete.set()

    for task in reversed(waiters):
        task._add_done_callback(done_callback)
        task._start_next()

    try:
        await complete
    except BaseException:
        cancel_remaining()
        raise

    idx = waiters.index(first_completed) if first_completed is not None else None
    return idx, tuple(waiters)


async def select(*awaitables: Awaitable[T]) -> tuple[int, T]:
    r"""Await on all given *awaitables* concurrently and return the index and result of the first to complete.

    After the first *awaitable* completes, whether through cancellation, exception, or success,
    the remaining *awaitables* are cancelled.
    Control returns to the caller after all remaining *awaitables* have finished cancelling.
    The result of the first completed *awaitable* is returned, or the exception is re-raised, if it failed.

    This function makes the same safety guarantees as :func:`!wait` regarding cancellation and clean-up.

    .. note::
        This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments,
        only :term:`coroutines <coroutine>`,  :term:`triggers <trigger>`, or other user-defined :term:`!awaitables`.

    .. note::
        It is possible for multiple *awaitables* to complete at the same time,
        however due to how the cocotb scheduler works, only one will complete *first*.
        It is good practice to avoid relying on the order of completion of multiple *awaitables* which complete at the same time.

    Args:
        awaitables: The :class:`~collections.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.

    Returns:
        A tuple comprised of the index into the argument list (0-based) of the first *awaitable* to complete and the *awaitable*'s result.

    Raises:
        ValueError: If no *awaitables* are provided.

    .. versionadded:: 2.1
    """
    if len(awaitables) == 0:
        raise ValueError("At least one awaitable required")

    def _repr() -> str:
        return f"select({', '.join(repr(a) for a in awaitables)})"

    idx, tasks = await _wait(awaitables, "FIRST_COMPLETED", _repr)
    assert idx is not None
    return idx, tasks[idx].result()


@overload
async def gather(a: Awaitable[T], /) -> tuple[T]: ...


@overload
async def gather(a: Awaitable[T], b: Awaitable[T2], /) -> tuple[T, T2]: ...


@overload
async def gather(
    a: Awaitable[T], b: Awaitable[T2], c: Awaitable[T3], /
) -> tuple[T, T2, T3]: ...


@overload
async def gather(
    a: Awaitable[T], b: Awaitable[T2], c: Awaitable[T3], d: Awaitable[T4], /
) -> tuple[T, T2, T3, T4]: ...


@overload
async def gather(*aw: Awaitable[T]) -> tuple[T, ...]: ...


async def gather(*awaitables: Awaitable[Any]) -> tuple[Any, ...]:
    r"""Await on all given *awaitables* concurrently and return their results once all have completed.

    If any *awaitable* results in an exception or is cancelled,
    the remaining *awaitables* are cancelled.
    Once all remaining *awaitables* have been cancelled, the call to :func:`!gather` re-raises the exception.

    This function makes the same safety guarantees as :func:`!wait` regarding cancellation and clean-up.

    .. note::
        This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments,
        only :term:`coroutines <coroutine>`,  :term:`triggers <trigger>`, or other user-defined :term:`!awaitables`.

    Args:
        awaitables: The :class:`~collections.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.

    Returns:
        A tuple of the results of awaiting each *awaitable* in the same order they were given.
        The order of the return tuple corresponds to the order of the input.

    .. versionadded:: 2.1
    """
    if len(awaitables) == 0:
        return ()

    def _repr() -> str:
        return f"gather({', '.join(repr(a) for a in awaitables)})"

    idx, tasks = await _wait(awaitables, "FIRST_EXCEPTION", _repr)

    if idx is not None:
        # There was a failure, so re-raise it.
        return tasks[idx].result()
    else:
        # All tasks completed successfully, so return their results.
        return tuple(task.result() for task in tasks)
