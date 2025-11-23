from __future__ import annotations

from collections.abc import Generator

import pytest

import cocotb
from cocotb.triggers import NullTrigger, Timer, Trigger, gather, select, wait


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
async def test_wait(_: object) -> None:
    a1, b1, c1, d1 = await wait(
        coro(1),
        Timer(2),
        AwaitableThing(3),
        raises_after(4),
        return_when="ALL_COMPLETED",
    )
    assert a1.done()
    assert b1.done()
    assert c1.done()
    assert d1.exception() is not None

    a2, b2, c2 = await wait(
        coro(1), Timer(2), AwaitableThing(3), return_when="FIRST_EXCEPTION"
    )
    assert a2.done()
    assert b2.done()
    assert c2.done()

    a3, b3, c3, d3 = await wait(
        Timer(1),
        raises_after(2),
        AwaitableThing(3),
        coro(4),
        return_when="FIRST_EXCEPTION",
    )
    # Wait for cancellations to finish
    await NullTrigger()
    assert a3.done()
    assert b3.exception() is not None
    assert c3.cancelled()
    assert d3.cancelled()

    a4, b4, c4, d4 = await wait(
        coro(1),
        Timer(2),
        AwaitableThing(3),
        raises_after(4),
        return_when="FIRST_COMPLETED",
    )
    # Wait for cancellations to finish
    await NullTrigger()
    assert a4.done()
    assert b4.cancelled()
    assert c4.cancelled()
    assert d4.cancelled()


@cocotb.test
async def test_wait_doesnt_cancel_tasks(_: object) -> None:
    async def completes() -> int:
        await Timer(10)
        return 123

    task = cocotb.start_soon(completes())
    await wait(task, Timer(1), return_when="FIRST_COMPLETED")
    await NullTrigger()
    assert not task.cancelled()
    assert await task == 123


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
        return_exception=True,
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
        return_exception=True,
    )
    assert idx == 0
    assert isinstance(res3, MyException)

    with pytest.raises(ValueError):
        await select()


@cocotb.test
async def test_cancel_while_waiting(_: object) -> None:
    async def waiter() -> None:
        await wait(Timer(2), return_when="ALL_COMPLETED")

    task = cocotb.start_soon(waiter())
    await Timer(1)
    task.cancel()
    await Timer(1)
