# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from collections.abc import Iterable
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Literal, TypeVar, overload

from cocotb._base_triggers import _InternalEvent
from cocotb.task import Task

if TYPE_CHECKING:
    from collections.abc import Awaitable


class ReturnWhen(Enum):
    FIRST_COMPLETED = auto()
    FIRST_EXCEPTION = auto()
    ALL_COMPLETED = auto()


T = TypeVar("T")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")


def _return_exception(task: Task[T]) -> BaseException | T:
    try:
        return task.result()
    except BaseException as e:
        return e


async def _wait(
    awaitables: Iterable[Awaitable[Any]],
    return_when: ReturnWhen,
    _repr: Callable[[], str],
) -> tuple[list[Task[Any]], Task[Any] | None]:
    r"""Await on all given *awaitables* concurrently and block until the *return_when* condition is met.

    Every :class:`~collections.abc.Awaitable` given to the function is :keyword:`await`\ ed concurrently in its own :class:`~cocotb.task.Task`.
    When the return conditions specified by *return_when* are met, this function returns those :class:`!Task`\ s.
    Once the return conditions are met, any waiter tasks which are still running are cancelled.
    This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments, only the waiter tasks.

    The *return_when* condition must be one of the following:

    - ``"FIRST_COMPLETED"``: Returns after the first of the *awaitables* completes, regardless if that was due to an exception or not.
    - ``"FIRST_EXCEPTION"``: Returns after all *awaitables* complete or after the first *awaitable* that completes due to an exception.
    - ``"ALL_COMPLETED"``: Returns after all *awaitables* complete.

    Must not be called with an empty ``awaitables`` (would hang forever).

    Args:
        awaitables: The :class:`~collections.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.
        return_when:
            The condition that must be met before returning.
            One of ``"FIRST_COMPLETED"``, ``"FIRST_EXCEPTION"``, or ``"ALL_COMPLETED"``.

    Returns:
        A tuple of waiter :class:`~cocotb.task.Task`\ s and the first completed :class:`~cocotb.task.Task` in
        ``FIRST_COMPLETED`` or ``FIRST_EXCEPTION`` mode, or ``None`` in ``ALL_COMPLETED`` mode.
        The order of the return tuple corresponds to the order of the input.

    .. versionadded:: 2.1
    """

    async def waiter(aw: Awaitable[T]) -> T:
        return await aw

    waiters = [Task[Any](waiter(a)) for a in awaitables]
    # Use dict (insertion-ordered) so cancellation order is deterministic and we have O(1) insertion and removals.
    remaining = dict.fromkeys(waiters)
    # Set when we meet the return condition.
    done = _InternalEvent(_repr)
    # Set when all tasks have completed, regardless of reason.
    complete = _InternalEvent(_repr)
    # The first task to complete, stored regardless of return_when condition.
    first_completed: Task[Any] | None = None

    if return_when == ReturnWhen.FIRST_COMPLETED:

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                complete.set()
            nonlocal first_completed
            if first_completed is None:
                first_completed = task
                done.set()

    elif return_when == ReturnWhen.FIRST_EXCEPTION:

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                done.set()
                complete.set()
            nonlocal first_completed
            if first_completed is None and (
                task.cancelled() or task.exception() is not None
            ):
                first_completed = task
                done.set()

    else:

        def done_callback(task: Task[Any]) -> None:
            del remaining[task]
            if not remaining:
                done.set()
                complete.set()

    for task in reversed(waiters):
        task._add_done_callback(done_callback)
        task._start_next()

    try:
        await done
    finally:
        # Cancel remaining tasks. No-op if everything has finished (ALL_COMPLETED)
        # or the return_when condition is specified, but all tasks happen to complete
        # before this Task runs again. Cancels whatever is remaining and rethrows if
        # the caller is cancelled.
        for task in remaining:
            task.cancel()

    # Wait until all children tasks have finished before returning.
    # Ensures any side-effectful clean-up has completed.
    if not complete.is_set():
        await complete

    return waiters, first_completed


@overload
async def select(
    *awaitables: Awaitable[T], return_exceptions: Literal[False] = False
) -> tuple[int, T]: ...


@overload
async def select(
    *awaitables: Awaitable[T], return_exceptions: Literal[True]
) -> tuple[int, T | BaseException]: ...


async def select(
    *awaitables: Awaitable[T],
    return_exceptions: bool = False,
    _repr: Callable[[], str] | None = None,
) -> tuple[int, T | BaseException]:
    r"""Await on all given *awaitables* concurrently and return the index and result of the first to complete.

    Regardless of the value of *return_exceptions*, after the first *awaitable* completes, whether it was cancelled, resulted in an exception, or resulted in a value,
    the remaining *awaitables* are cancelled.
    This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments, only :term:`coroutines <coroutine>`,  :term:`triggers <trigger>`, or other user-defined :term:`!awaitables`.
    Control returns to the caller after all *awaitables* have completed and/or been cancelled.

    Regardless of the value of *return_exceptions*, if the task awaiting a call to this function is cancelled before completion,
    all *awaitables* which have not yet completed are cancelled and :exc:`!CancelledError` is raised.

    It is possible for multiple *awaitables* to complete at the same time,
    however due to how the cocotb scheduler works, only one will complete *first*.
    It is good practice to avoid relying on the order of completion of multiple *awaitables* which complete at the same time.

    Args:
        awaitables: The :class:`~collections.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.
        return_exceptions:
            If ``False`` (default), re-raises the exception when an *awaitable* results in an exception.
            If ``True``, returns the exception rather than re-raising when an *awaitable* results in an exception.

    Returns:
        A tuple comprised of the index into the argument list (0-based) of the first *awaitable* to complete, and the *awaitable*'s result.

    Raises:
        ValueError: If no *awaitables* are provided.

    .. versionadded:: 2.1
    """
    if len(awaitables) == 0:
        raise ValueError("At least one awaitable required")

    # select is being called on its own and not part of First.
    # So we add a repr here since this is not a class.
    if _repr is None:

        def _repr() -> str:
            return f"select({', '.join(repr(a) for a in awaitables)})"

    tasks, first_completed = await _wait(
        awaitables, return_when=ReturnWhen.FIRST_COMPLETED, _repr=_repr
    )
    assert first_completed is not None

    idx = tasks.index(first_completed)
    if return_exceptions:
        return (idx, _return_exception(first_completed))
    else:
        # This will raise CancelledError if the task was cancelled, or the exception if it failed,
        # or return the result if it succeeded.
        return idx, first_completed.result()


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
    _repr: Callable[[], str] | None = None,
) -> tuple[Any, ...]:
    r"""Await on all given *awaitables* concurrently and return their results once all have completed.

    When *return_exceptions* is ``False``, if any *awaitable* results in an exception or is cancelled,
    the remaining *awaitables* are cancelled and the exception or :exc:`~asyncio.CancelledError` is re-raised.
    This does not cancel :class:`~cocotb.task.Task`\ s passed as arguments, only :term:`coroutines <coroutine>`,  :term:`triggers <trigger>`, or other user-defined :term:`!awaitables`.
    When *return_exceptions* is ``True``, all exceptions and cancellations are treated as successful results and returned in the resulting tuple.
    Control returns to the caller after all *awaitables* have completed and/or been cancelled.

    Regardless of the value of *return_exceptions*, if the task awaiting a call to this function is cancelled before completion,
    all *awaitables* which have not yet completed are cancelled and :exc:`!CancelledError` is raised.

    Args:
        awaitables: The :class:`~collections.abc.Awaitable`\ s to concurrently :keyword:`!await` upon.
        return_exceptions:
            If ``False`` (default), after the first *awaitable* results in an exception or cancellation,
            cancels the remaining *awaitables* and re-raises the exception or :exc:`!CancelledError`.
            If ``True``, returns all exceptions or :exc:`!CancelledError` rather than the result value when an *awaitable* results in an exception.

    Returns:
        A tuple of the results of awaiting each *awaitable* in the same order they were given.
        The order of the return tuple corresponds to the order of the input.

    .. versionadded:: 2.1
    """
    if len(awaitables) == 0:
        return ()

    # gather is being called on its own and not part of Combine.
    # So we add a repr here since this is not a class.
    if _repr is None:

        def _repr() -> str:
            return f"gather({', '.join(repr(a) for a in awaitables)})"

    # When returning exceptions, we behave like continue-on-error: never cancel siblings.
    # Otherwise, cancel siblings as soon as one fails or is cancelled.
    tasks, first_completed = await _wait(
        awaitables,
        return_when=ReturnWhen.ALL_COMPLETED
        if return_exceptions
        else ReturnWhen.FIRST_EXCEPTION,
        _repr=_repr,
    )

    if return_exceptions:
        return tuple(_return_exception(task) for task in tasks)
    elif first_completed is not None:
        # first_completed is only set in FIRST_EXCEPTION mode when a task fails or is cancelled.
        # Calling result() will cause the exception or CancelledError to be re-raised.
        # Wrapped in a tuple to make mypy happy about the return type.
        return (first_completed.result(),)
    else:
        return tuple(task.result() for task in tasks)
