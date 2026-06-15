# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from asyncio import CancelledError
from collections.abc import Generator

import pytest

import cocotb
from cocotb.triggers import NullTrigger, Timer, Trigger, gather, select


async def coro(wait: int, ret: int = 0) -> int:
    await Timer(wait)
    return ret


class AwaitableThing:
    def __init__(self, wait: int, ret: int = 0) -> None:
        self._wait = wait
        self._ret = ret

    def __await__(self) -> Generator[Trigger, None, int]:
        yield from coro(self._wait).__await__()
        return self._ret


class MyException(Exception): ...


async def raises_after(wait: int) -> None:
    await Timer(wait)
    raise MyException()


@cocotb.test
async def test_gather(_: object) -> None:
    timer1 = Timer(1)
    a1, b1, c1 = await gather(
        coro(wait=3, ret=123),
        AwaitableThing(2, ret=9),
        timer1,
    )
    assert a1 == 123
    assert b1 == 9
    assert c1 == timer1

    with pytest.raises(MyException):
        await gather(
            raises_after(wait=3),
            AwaitableThing(2, ret=9),
            Timer(1),
        )

    timer2 = Timer(2)
    a2, b2, c2 = await gather(
        raises_after(wait=3),
        AwaitableThing(1, ret=56),
        timer2,
        return_exceptions=True,
    )
    assert isinstance(a2, MyException)
    assert b2 == 56
    assert c2 == timer2

    assert await gather() == ()


@cocotb.test
async def test_select(_: object) -> None:
    timer1 = Timer(1)
    idx, res1 = await select(
        coro(wait=3, ret=123),
        AwaitableThing(2, ret=9),
        timer1,
    )
    assert idx == 2
    assert res1 == timer1

    idx, res2 = await select(
        raises_after(wait=3),
        AwaitableThing(1, ret=31),
        Timer(2),
        return_exceptions=True,
    )
    assert idx == 1
    assert res2 == 31
    await Timer(5)  # ensure failing task was killed

    with pytest.raises(MyException):
        await select(
            raises_after(wait=1),
            AwaitableThing(2, ret=9),
            Timer(3),
        )

    idx, res3 = await select(
        raises_after(wait=1),
        AwaitableThing(2, ret=12),
        Timer(3),
        return_exceptions=True,
    )
    assert idx == 0
    assert isinstance(res3, MyException)

    with pytest.raises(ValueError):
        await select()


@cocotb.test
async def test_gather_single(_: object) -> None:
    """gather with one awaitable still returns a single-element tuple."""
    (result,) = await gather(coro(wait=1, ret=42))
    assert result == 42


@cocotb.test
async def test_select_single(_: object) -> None:
    """select with one awaitable returns index 0 and its result."""
    idx, res = await select(coro(wait=1, ret=42))
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
async def test_gather_outer_cancel_return_exceptions(_: object) -> None:
    """return_exceptions=True must NOT swallow outer cancellation."""
    child_completed = False

    async def child() -> None:
        nonlocal child_completed
        await Timer(10)
        child_completed = True

    async def waiter() -> None:
        await gather(child(), Timer(20), return_exceptions=True)

    task = cocotb.start_soon(waiter())
    await Timer(1)
    task.cancel()
    await Timer(1)
    assert task.cancelled(), (
        "outer cancellation should propagate even with return_exceptions=True"
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
    """When a child is cancelled and return_exceptions=False, gather re-raises CancelledError
    and cancels the remaining children."""
    sibling_completed = False

    async def sibling() -> None:
        nonlocal sibling_completed
        await Timer(10)
        sibling_completed = True

    victim_task = cocotb.start_soon(coro(wait=20, ret=0))

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
async def test_gather_child_cancelled_return_exceptions(_: object) -> None:
    """When a child is cancelled and return_exceptions=True, gather returns CancelledError
    in the tuple and other children continue."""
    victim_task = cocotb.start_soon(coro(wait=20, ret=0))

    async def waiter() -> tuple[object, ...]:
        return await gather(victim_task, coro(wait=10, ret=99), return_exceptions=True)

    task = cocotb.start_soon(waiter())
    await Timer(1)
    victim_task.cancel()
    await Timer(15)
    assert task.done()
    a, b = task.result()
    assert isinstance(a, CancelledError)
    assert b == 99


@cocotb.test
async def test_select_child_cancelled(_: object) -> None:
    """When the winning child was cancelled, select raises CancelledError by default
    and returns it when return_exception=True."""
    victim_task = cocotb.start_soon(coro(wait=20, ret=0))

    async def waiter_raises() -> None:
        await select(victim_task, Timer(30))

    t1 = cocotb.start_soon(waiter_raises())
    await Timer(1)
    victim_task.cancel()
    await Timer(2)
    assert t1.done()
    assert isinstance(t1.exception(), CancelledError)

    victim_task2 = cocotb.start_soon(coro(wait=20, ret=0))

    async def waiter_returns() -> tuple[int, object]:
        return await select(victim_task2, Timer(30), return_exception=True)

    t2 = cocotb.start_soon(waiter_returns())
    await Timer(1)
    victim_task2.cancel()
    await Timer(2)
    assert t2.done()
    idx, exc = t2.result()
    assert idx == 0
    assert isinstance(exc, CancelledError)


@cocotb.test
async def test_gather_preserves_cancel_message(_: object) -> None:
    """When return_exceptions=True, the original CancelledError instance (with its message)
    is returned, not a fresh one."""
    victim_task = cocotb.start_soon(coro(wait=20, ret=0))

    async def waiter() -> tuple[object, ...]:
        return await gather(victim_task, coro(wait=5, ret=1), return_exceptions=True)

    task = cocotb.start_soon(waiter())
    await Timer(1)
    victim_task.cancel("specific reason")
    await Timer(10)
    assert task.done()
    a, _ = task.result()
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
        await gather(task, raises_after(wait=1))
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
