from __future__ import annotations

import sys

import cocotb
from cocotb.triggers import (
    SimTimeoutError,
    Timer,
    with_timeout,
)

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup


from cocotb.triggers import TaskManager


@cocotb.test
async def test_with_timeout_argument_combinations(dut) -> None:
    trigger = Timer(1, "ns")
    assert await with_timeout(trigger, 10, "ns") is trigger

    trigger = Timer(1, "ns")
    assert await with_timeout(trigger, timeout_time=10, timeout_unit="ns") is trigger

    trigger = Timer(1, "ns")
    assert (
        await with_timeout(
            trigger, timeout_time=10, timeout_unit="ns", round_mode="error"
        )
        is trigger
    )

    trigger = Timer(1, "ns")
    assert await with_timeout(10, "ns", trigger=trigger) is trigger

    trigger = Timer(1, "ns")
    assert (
        await with_timeout(trigger=trigger, timeout_time=10, timeout_unit="ns")
        is trigger
    )


@cocotb.test
async def test_with_timeout_decorator_argument_combinations(dut) -> None:
    @with_timeout(10, "ns")
    async def positional() -> str:
        await Timer(1, "ns")
        return "positional"

    @with_timeout(timeout_time=10, timeout_unit="ns")
    async def keyword() -> str:
        await Timer(1, "ns")
        return "keyword"

    assert await positional() == "positional"
    assert await keyword() == "keyword"


@cocotb.test
@cocotb.xfail(raises=SimTimeoutError)
@with_timeout(timeout_time=10, timeout_unit="ns")
async def test_with_timeout_decorator(dut) -> None:
    await Timer(20, "ns")


@cocotb.test
async def test_with_timeout_decorator_with_fork(dut) -> None:
    async def foo():
        async with TaskManager() as tm:

            @tm.fork
            @with_timeout(10, "ns")
            async def my_thing():
                await Timer(20, "ns")

    task = cocotb.start_soon(foo())
    try:
        await task
    except BaseExceptionGroup as e:
        my_exc, rest = e.split(SimTimeoutError)
        assert rest is None
        assert my_exc is not None
        assert len(my_exc.exceptions) == 1
