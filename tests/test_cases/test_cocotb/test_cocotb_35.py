"""
This file contains tests that use syntax introduced in Python 3.5.

This is likely to mean this file only tests `async def` functions.
"""

import cocotb
from cocotb.triggers import Timer
from cocotb.outcomes import Value, Error
from cocotb.result import TestFailure


class produce:
    """ Test helpers that produce a value / exception in different ways """
    @staticmethod
    @cocotb.coroutine
    def coro(outcome):
        yield Timer(1)
        return outcome.get()

    @staticmethod
    @cocotb.coroutine
    async def async_annotated(outcome):
        await Timer(1)
        return outcome.get()

    @staticmethod
    async def async_(outcome):
        await Timer(1)
        return outcome.get()


class SomeException(Exception):
    """ Custom exception to test for that can't be thrown by internals """
    pass


# just to be sure...
@cocotb.test(expect_fail=True)
async def test_async_test_can_fail(dut):
    await Timer(1)
    raise TestFailure


@cocotb.test()
def test_annotated_async_from_coro(dut):
    """
    Test that normal coroutines are able to call async functions annotated
    with `@cocotb.coroutine`
    """
    v = yield produce.async_annotated(Value(1))
    assert v == 1

    try:
        yield produce.async_annotated(Error(SomeException))
    except SomeException:
        pass
    else:
        assert False


@cocotb.test()
async def test_annotated_async_from_async(dut):
    """ Test that async coroutines are able to call themselves """
    v = await produce.async_annotated(Value(1))
    assert v == 1

    try:
        await produce.async_annotated(Error(SomeException))
    except SomeException:
        pass
    else:
        assert False


@cocotb.test()
async def test_annotated_async_from_async(dut):
    """ Test that async coroutines are able to call raw async functions """
    v = await produce.async_(Value(1))
    assert v == 1

    try:
        await produce.async_(Error(SomeException))
    except SomeException:
        pass
    else:
        assert False


@cocotb.test()
async def test_coro_from_async(dut):
    """ Test that async coroutines are able to call regular ones """
    v = await produce.coro(Value(1))
    assert v == 1

    try:
        await produce.coro(Error(SomeException))
    except SomeException:
        pass
    else:
        assert False


@cocotb.test()
async def test_trigger_await_gives_self(dut):
    """ Test that await returns the trigger itself for triggers """
    t = Timer(1)
    t2 = await t
    assert t2 is t


@cocotb.test()
async def test_await_causes_start(dut):
    """ Test that an annotated async coroutine gets marked as started """
    coro = produce.async_annotated(Value(1))
    assert not coro.has_started()
    await coro
    assert coro.has_started()


@cocotb.test()
def test_undecorated_coroutine_fork(dut):
    ran = False

    async def example():
        nonlocal ran
        await cocotb.triggers.Timer(1, 'ns')
        ran = True

    yield cocotb.fork(example()).join()
    assert ran

@cocotb.test()
def test_undecorated_coroutine_yield(dut):
    ran = False

    async def example():
        nonlocal ran
        await cocotb.triggers.Timer(1, 'ns')
        ran = True

    yield example()
    assert ran


# these tests should run in definition order, not lexicographic order
last_ordered_test = None


@cocotb.test()
async def test_ordering_3(dut):
    global last_ordered_test
    val, last_ordered_test = last_ordered_test, 3
    assert val is None


@cocotb.test()
async def test_ordering_2(dut):
    global last_ordered_test
    val, last_ordered_test = last_ordered_test, 2
    assert val == 3


@cocotb.test()
async def test_ordering_1(dut):
    global last_ordered_test
    val, last_ordered_test = last_ordered_test, 1
    assert val == 2

