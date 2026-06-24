# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from asyncio import CancelledError
from collections.abc import Generator

import pytest

import cocotb
from cocotb.triggers import NullTrigger, Timer, Trigger, gather, select, wait


async def coro(delay: int, ret: int = 0) -> int:
    await Timer(delay)
    return ret


class AwaitableThing:
    def __init__(self, delay: int, ret: int = 0) -> None:
        self._delay = delay
        self._ret = ret

    def __await__(self) -> Generator[Trigger, None, int]:
        yield from coro(self._delay).__await__()
        return self._ret


class MyException(Exception): ...


async def raises_after(delay: int) -> None:
    await Timer(delay)
    raise MyException()


@cocotb.test
async def test_gather(_: object) -> None:
    timer1 = Timer(1)
    a1, b1, c1 = await gather(
        coro(delay=3, ret=123),
        AwaitableThing(2, ret=9),
        timer1,
    )
    assert a1 == 123
    assert b1 == 9
    assert c1 == timer1

    with pytest.raises(MyException):
        await gather(
            raises_after(delay=3),
            AwaitableThing(2, ret=9),
            Timer(1),
        )

    assert await gather() == ()


@cocotb.test
async def test_select(_: object) -> None:
    timer1 = Timer(1)
    idx, res1 = await select(
        coro(delay=3, ret=123),
        AwaitableThing(2, ret=9),
        timer1,
    )
    assert idx == 2
    assert res1 == timer1

    with pytest.raises(MyException):
        await select(
            raises_after(delay=1),
            AwaitableThing(2, ret=9),
            Timer(3),
        )

    with pytest.raises(ValueError):
        await select()


@cocotb.test
async def test_wait_empty(_: object) -> None:
    """wait() with no awaitables raises ValueError for every return_when mode."""
    with pytest.raises(ValueError):
        await wait(return_when="FIRST_COMPLETED")  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        await wait(return_when="FIRST_EXCEPTION")  # type: ignore[call-overload]
    with pytest.raises(ValueError):
        await wait(return_when="ALL_COMPLETED")  # type: ignore[call-overload]


@cocotb.test
async def test_wait_all_completed(_: object) -> None:
    """wait() with ALL_COMPLETED returns after every awaitable is done, regardless of exceptions."""
    timer2 = Timer(2)
    idx, tasks = await wait(
        raises_after(delay=3),
        AwaitableThing(1, ret=56),
        timer2,
        return_when="ALL_COMPLETED",
    )
    assert idx is None
    assert isinstance(tasks[0].exception(), MyException)
    assert tasks[1].result() == 56
    assert tasks[2].result() == timer2


@cocotb.test
async def test_wait_first_completed(_: object) -> None:
    """wait() with FIRST_COMPLETED returns after the first awaitable completes."""
    idx, tasks = await wait(
        raises_after(delay=3),
        AwaitableThing(1, ret=31),
        Timer(2),
        return_when="FIRST_COMPLETED",
    )
    assert idx == 1
    assert tasks[1].result() == 31
    await Timer(5)  # ensure remaining tasks were killed
    assert tasks[0].cancelled()
    assert tasks[2].cancelled()


@cocotb.test
async def test_wait_first_exception(_: object) -> None:
    """wait() with FIRST_EXCEPTION returns at the first exception, or after all complete."""
    idx, tasks = await wait(
        raises_after(delay=1),
        AwaitableThing(2, ret=12),
        Timer(3),
        return_when="FIRST_EXCEPTION",
    )
    assert idx == 0
    assert isinstance(tasks[0].exception(), MyException)
    assert tasks[1].cancelled()
    assert tasks[2].cancelled()

    idx2, tasks2 = await wait(
        coro(delay=1, ret=7),
        AwaitableThing(2, ret=8),
        return_when="FIRST_EXCEPTION",
    )
    assert idx2 is None
    assert tasks2[0].result() == 7
    assert tasks2[1].result() == 8


@cocotb.test
async def test_gather_single(_: object) -> None:
    """gather with one awaitable still returns a single-element tuple."""
    (result,) = await gather(coro(delay=1, ret=42))
    assert result == 42


@cocotb.test
async def test_select_single(_: object) -> None:
    """select with one awaitable returns index 0 and its result."""
    idx, res = await select(coro(delay=1, ret=42))
    assert idx == 0
    assert res == 42


@cocotb.test
async def test_gather_outer_cancel(_: object) -> None:
    """Cancelling the task awaiting gather propagates CancelledError and cancels children."""
    child_completed = False

    async def child() -> None:
        nonlocal child_completed
        await Timer(10)
        child_completed = True

    async def waiter() -> None:
        await gather(child(), Timer(20))

    task = cocotb.start_soon(waiter())
    await Timer(1)
    task.cancel()
    await Timer(1)
    assert task.cancelled()
    # Children were cancelled before they could finish.
    assert not child_completed


@cocotb.test
async def test_wait_outer_cancel_all_completed(_: object) -> None:
    """Cancelling the task awaiting wait(ALL_COMPLETED) propagates CancelledError and cancels children."""
    child_completed = False

    async def child() -> None:
        nonlocal child_completed
        await Timer(10)
        child_completed = True

    async def waiter() -> None:
        await wait(child(), Timer(20), return_when="ALL_COMPLETED")

    task = cocotb.start_soon(waiter())
    await Timer(1)
    task.cancel()
    await Timer(1)
    assert task.cancelled(), (
        "outer cancellation should propagate even with ALL_COMPLETED"
    )
    assert not child_completed


@cocotb.test
async def test_select_outer_cancel(_: object) -> None:
    """Cancelling the task awaiting select propagates CancelledError and cancels children."""
    child_completed = False

    async def child() -> None:
        nonlocal child_completed
        await Timer(10)
        child_completed = True

    async def waiter() -> None:
        await select(child(), Timer(20))

    task = cocotb.start_soon(waiter())
    await Timer(1)
    task.cancel()
    await Timer(1)
    assert task.cancelled()
    assert not child_completed


@cocotb.test
async def test_gather_child_cancelled_default(_: object) -> None:
    """When a child is cancelled, gather re-raises CancelledError and cancels the remaining children."""
    sibling_completed = False

    async def sibling() -> None:
        nonlocal sibling_completed
        await Timer(10)
        sibling_completed = True

    victim_task = cocotb.start_soon(coro(delay=20, ret=0))

    async def waiter() -> None:
        await gather(victim_task, sibling())

    task = cocotb.start_soon(waiter())
    await Timer(1)
    victim_task.cancel()
    await Timer(2)
    assert task.done()
    assert isinstance(task.exception(), CancelledError)
    assert not sibling_completed


@cocotb.test
async def test_wait_child_cancelled_all_completed(_: object) -> None:
    """With wait(ALL_COMPLETED) a cancelled child does not stop other children, and the
    cancellation is observable as a cancelled waiter task."""
    victim_task = cocotb.start_soon(coro(delay=20, ret=0))

    async def waiter() -> tuple[int | None, tuple[object, ...]]:
        idx, tasks = await wait(
            victim_task, coro(delay=10, ret=99), return_when="ALL_COMPLETED"
        )
        return idx, tuple(t.exception() if t.cancelled() else t.result() for t in tasks)

    task = cocotb.start_soon(waiter())
    await Timer(1)
    victim_task.cancel()
    await Timer(15)
    assert task.done()
    idx, results = task.result()
    assert idx is None
    a, b = results
    assert isinstance(a, CancelledError)
    assert b == 99


@cocotb.test
async def test_select_child_cancelled(_: object) -> None:
    """When the winning child was cancelled, select raises CancelledError."""
    victim_task = cocotb.start_soon(coro(delay=20, ret=0))

    async def waiter_raises() -> None:
        await select(victim_task, Timer(30))

    t1 = cocotb.start_soon(waiter_raises())
    await Timer(1)
    victim_task.cancel()
    await Timer(2)
    assert t1.done()
    assert isinstance(t1.exception(), CancelledError)


@cocotb.test
async def test_wait_first_completed_child_cancelled(_: object) -> None:
    """When the winning child was cancelled, wait(FIRST_COMPLETED) returns it as a cancelled waiter task."""
    victim_task = cocotb.start_soon(coro(delay=20, ret=0))

    async def waiter() -> tuple[int | None, bool]:
        idx, tasks = await wait(victim_task, Timer(30), return_when="FIRST_COMPLETED")
        assert idx is not None
        return idx, tasks[idx].cancelled()

    t = cocotb.start_soon(waiter())
    await Timer(1)
    victim_task.cancel()
    await Timer(2)
    assert t.done()
    idx, was_cancelled = t.result()
    assert idx == 0
    assert was_cancelled


@cocotb.test
async def test_wait_preserves_cancel_message(_: object) -> None:
    """The original CancelledError instance (with its message) is preserved on the waiter task."""
    victim_task = cocotb.start_soon(coro(delay=20, ret=0))

    async def waiter() -> BaseException | None:
        _, tasks = await wait(
            victim_task, coro(delay=5, ret=1), return_when="ALL_COMPLETED"
        )
        return tasks[0].exception()

    task = cocotb.start_soon(waiter())
    await Timer(1)
    victim_task.cancel("specific reason")
    await Timer(10)
    assert task.done()
    a = task.result()
    assert isinstance(a, CancelledError)
    assert a.args == ("specific reason",), (
        f"expected original CancelledError message preserved, got args={a.args!r}"
    )


@cocotb.test
async def test_gather_does_not_cancel_passed_tasks(_: object) -> None:
    """Tasks passed to gather are not cancelled when gather tears down its waiters
    after a sibling fails."""

    async def completes() -> int:
        await Timer(10)
        return 7

    task = cocotb.start_soon(completes())
    # raises_after fires first; gather cancels the waiter wrapping `task`,
    # but `task` itself must keep running.
    with pytest.raises(MyException):
        await gather(task, raises_after(delay=1))
    await NullTrigger()
    assert not task.cancelled()
    assert await task == 7


@cocotb.test
async def test_select_does_not_cancel_passed_tasks(_: object) -> None:
    """Tasks passed to select are not cancelled when select returns (only internal waiters are)."""

    async def completes() -> int:
        await Timer(10)
        return 7

    task = cocotb.start_soon(completes())
    # Timer(1) wins; the waiter wrapping task is cancelled, but task itself keeps running.
    await select(task, Timer(1))
    await NullTrigger()
    assert not task.cancelled()
    assert await task == 7


@cocotb.test
async def test_wait_second_exception(_: object) -> None:
    async def do_nothing() -> int:
        return 123

    idx, tasks = await wait(
        do_nothing(),  # Will pass before the next two raise exceptions
        raises_after(delay=1),  # Will fail and kill the next task
        raises_after(delay=2),  # Will be cancelled
        return_when="FIRST_EXCEPTION",
    )
    assert idx == 1
    assert tasks[0].result() == 123
    assert isinstance(tasks[1].exception(), MyException)
    assert tasks[2].cancelled()
