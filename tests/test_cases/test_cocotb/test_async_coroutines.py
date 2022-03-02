# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Test function and substitutability of async coroutines
"""
import pytest
from common import MyException

import cocotb
from cocotb.outcomes import Error, Value
from cocotb.triggers import Timer


class produce:
    """Test helpers that produce a value / exception in different ways"""

    @staticmethod
    @cocotb.coroutine  # testing legacy coroutine against async func
    def coro(outcome):
        yield Timer(1)
        return outcome.get()

    @staticmethod
    @cocotb.coroutine  # testing coroutine decorator on async func
    async def async_annotated(outcome):
        await Timer(1)
        return outcome.get()

    @staticmethod
    async def async_(outcome):
        await Timer(1)
        return outcome.get()


@cocotb.test()  # test yielding decorated async coroutine in legacy coroutine
def test_annotated_async_from_coro(dut):
    """
    Test that normal coroutines are able to call async functions annotated
    with `@cocotb.coroutine`
    """
    v = yield produce.async_annotated(Value(1))
    assert v == 1

    try:
        yield produce.async_annotated(Error(MyException))
    except MyException:
        pass
    else:
        assert False


@cocotb.test()
async def test_annotated_async_from_async(dut):
    """Test that async coroutines are able to call themselves"""
    v = await produce.async_annotated(Value(1))
    assert v == 1

    try:
        await produce.async_annotated(Error(MyException))
    except MyException:
        pass
    else:
        assert False


@cocotb.test()
async def test_async_from_async(dut):
    """Test that async coroutines are able to call raw async functions"""
    v = await produce.async_(Value(1))
    assert v == 1

    try:
        await produce.async_(Error(MyException))
    except MyException:
        pass
    else:
        assert False


@cocotb.test()
async def test_coro_from_async(dut):
    """Test that async coroutines are able to call regular ones"""
    v = await produce.coro(Value(1))
    assert v == 1

    try:
        await produce.coro(Error(MyException))
    except MyException:
        pass
    else:
        assert False


@cocotb.test()
async def test_trigger_await_gives_self(dut):
    """Test that await returns the trigger itself for triggers"""
    t = Timer(1)
    t2 = await t
    assert t2 is t


@cocotb.test()
async def test_await_causes_start(dut):
    """Test that an annotated async coroutine gets marked as started"""
    coro = produce.async_annotated(Value(1))
    assert not coro.has_started()
    await coro
    assert coro.has_started()


@cocotb.test()  # test forking undecorated async coroutine in legacy coroutine
def test_undecorated_coroutine_start_soon(dut):
    ran = False

    async def example():
        nonlocal ran
        await cocotb.triggers.Timer(1, "ns")
        ran = True

    yield cocotb.start_soon(example()).join()
    assert ran


@cocotb.test()  # test yielding undecorated async coroutine in legacy coroutine
def test_undecorated_coroutine_yield(dut):
    ran = False

    async def example():
        nonlocal ran
        await cocotb.triggers.Timer(1, "ns")
        ran = True

    yield example()
    assert ran


@cocotb.test()
async def test_fork_coroutine_function_exception(dut):
    async def coro():
        pass

    pattern = (
        "Coroutine function {} should be called "
        "prior to being scheduled.".format(coro)
    )
    with pytest.raises(TypeError, match=pattern):
        cocotb.start_soon(coro)


@cocotb.test()
async def test_task_coroutine_function_exception(dut):
    async def coro(dut):
        pass

    pattern = (
        "Coroutine function {} should be called "
        "prior to being scheduled.".format(coro)
    )
    with pytest.raises(TypeError, match=pattern):
        cocotb.decorators.Task(coro)
