# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import threading
import time

import pytest

import cocotb
from cocotb.clock import Clock
from cocotb.task import bridge, resume
from cocotb.triggers import ReadOnly, RisingEdge, Timer
from cocotb.utils import get_sim_steps, get_sim_time


def return_two(dut):
    return 2


@resume
async def await_two_clock_edges(dut):
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    cocotb.log.info("Returning from await_two_clock_edges")
    return 2


def calls_resume(dut):
    return await_two_clock_edges(dut)


def print_sim_time(dut, base_time):
    # We are not calling out here so time should not advance
    # And should also remain consistent
    for _ in range(5):
        time.sleep(0.02)
        assert get_sim_time("step") == base_time


@cocotb.test()
async def test_time_in_bridge(dut):
    """
    Test that the simulation time does not advance if the wrapped blocking
    routine does not call @resume
    """
    await Timer(10, unit="ns")
    time = get_sim_time("step")
    for _ in range(10):
        await bridge(print_sim_time)(dut, time)

    time_now = get_sim_time("step")
    await Timer(10, unit="ns")

    assert time == time_now


@cocotb.test()
async def test_time_in_resume(dut):
    """
    Test that an @bridge function calling back into a cocotb @resume
    takes the expected amount of time
    """

    @resume
    async def wait_cycles(dut, n):
        for _ in range(n):
            await RisingEdge(dut.clk)

    @bridge
    def wait_cycles_wrapper(dut, n):
        return wait_cycles(dut, n)

    cocotb.start_soon(Clock(dut.clk, 100, unit="ns").start())
    await Timer(10, unit="ns")
    for n in range(5):
        for _ in range(20):
            await RisingEdge(dut.clk)
            time = get_sim_time("step")
            expected_after = time + get_sim_steps(100, "ns") * n
            await wait_cycles_wrapper(dut, n)
            time_after = get_sim_time("step")
            assert expected_after == time_after


@cocotb.test()
async def test_blocking_function_call_return(dut):
    """
    Test ability to await a blocking function that is not a coroutine using @bridge
    """

    async def clock_monitor(dut):
        count = 0
        while True:
            await RisingEdge(dut.clk)
            await Timer(1000, unit="ns")
            count += 1

    cocotb.start_soon(clock_monitor(dut))
    cocotb.start_soon(Clock(dut.clk, 100, unit="ns").start())
    value = await bridge(return_two)(dut)
    assert value == 2


@cocotb.test()
async def test_consecutive_bridges(dut):
    """
    Test that multiple @bridge functions can be called in the same test
    """
    value = await bridge(return_two)(dut)
    cocotb.log.info("First one completed")
    assert value == 2

    value = await bridge(return_two)(dut)
    cocotb.log.info("Second one completed")
    assert value == 2


@cocotb.test()
async def test_bridge_from_readonly(dut):
    """
    Test that @bridge functions that don't consume simulation time
    can be called from ReadOnly state
    """
    await ReadOnly()
    cocotb.log.info("In readonly")
    value = await bridge(return_two)(dut)
    assert value == 2


@cocotb.test()
async def test_resume_from_readonly(dut):
    """
    Test that @bridge functions that call @resumes that await Triggers
    can be called from ReadOnly state
    """
    cocotb.start_soon(Clock(dut.clk, 100, unit="ns").start())

    await ReadOnly()
    cocotb.log.info("In readonly")
    value = await bridge(calls_resume)(dut)
    assert value == 2


@cocotb.test()
async def test_resume_that_awaits(dut):
    """
    Test that @bridge functions can call @resume coroutines that
    awaits Triggers and return values back through to
    the test
    """
    cocotb.start_soon(Clock(dut.clk, 100, unit="ns").start())

    value = await bridge(calls_resume)(dut)
    assert value == 2


@cocotb.test()
async def test_await_after_bridge(dut):
    """
    Test that awaiting a Trigger works after returning
    from @bridge functions that call @resumes that consume
    simulation time
    """
    cocotb.start_soon(Clock(dut.clk, 100, unit="ns").start())

    value = await bridge(calls_resume)(dut)
    assert value == 2

    await Timer(10, unit="ns")
    await RisingEdge(dut.clk)


@cocotb.test()
async def test_bridge_from_start_soon(dut):
    """
    Test that @bridge functions work when awaited from a forked
    task
    """

    async def run_function(dut):
        value = await bridge(calls_resume)(dut)
        return value

    async def run_bridge(dut):
        value = await bridge(return_two)(dut)
        return value

    cocotb.start_soon(Clock(dut.clk, 100, unit="ns").start())

    coro1 = cocotb.start_soon(run_function(dut))
    value = await coro1
    assert value == 2
    cocotb.log.info("Back from join 1")

    value = 0
    coro2 = cocotb.start_soon(run_bridge(dut))
    value = await coro2
    assert value == 2
    cocotb.log.info("Back from join 2")


@cocotb.test()
async def test_bridge_raised_exception(dut):
    """
    Test that exceptions thrown by @bridge functions can be caught
    """

    @bridge
    def func():
        raise ValueError()

    with pytest.raises(ValueError):
        await func()


@cocotb.test()
async def test_bridge_returns_exception(dut):
    """
    Test that exceptions can be returned by @bridge functions
    """

    @bridge
    def func():
        return ValueError()

    result = await func()

    assert isinstance(result, ValueError)


@cocotb.test()
async def test_resume_raised_exception(dut):
    """
    Test that exceptions thrown by @resume coroutines can be caught
    """

    @resume
    async def func():
        raise ValueError()

    @bridge
    def ext():
        return func()

    with pytest.raises(ValueError):
        await ext()


@cocotb.test()
async def test_resume_returns_exception(dut):
    """
    Test that exceptions can be returned by @resume coroutines
    """

    @resume
    async def gen_func():
        return ValueError()

    @bridge
    def ext():
        return gen_func()

    result = await ext()

    assert isinstance(result, ValueError)


@cocotb.test()
async def test_resume_from_weird_thread_fails(dut):
    """
    Test that background threads calling a @resume do not hang forever
    """
    func_started = False
    caller_resumed = False
    raised = False

    @resume
    async def func():
        nonlocal func_started
        func_started = True
        await Timer(10, unit="ns")

    def function_caller():
        nonlocal raised
        nonlocal caller_resumed
        try:
            func()
        except RuntimeError:
            raised = True
        finally:
            caller_resumed = True

    @bridge
    def ext():
        t = threading.Thread(target=function_caller)
        t.start()
        t.join()

    task = cocotb.start_soon(ext())

    await Timer(20, unit="ns")

    assert caller_resumed, "Caller was never resumed"
    assert not func_started, "Function should never have started"
    assert raised, "No exception was raised to warn the user"

    await task


@cocotb.test()
async def test_resume_called_in_parallel(dut):
    """
    Test that the same `@resume` can be called from two parallel background
    threads.
    """

    @resume
    async def function(x):
        await Timer(1, unit="ns")
        return x

    @bridge
    def call_function(x):
        return function(x)

    t1 = cocotb.start_soon(call_function(1))
    t2 = cocotb.start_soon(call_function(2))
    v1 = await t1
    v2 = await t2
    assert v1 == 1, v1
    assert v2 == 2, v2
