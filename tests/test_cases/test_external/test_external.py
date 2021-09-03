# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
A set of tests that demonstrate cocotb functionality

Also used a regression test of cocotb capabilities
"""
import threading

import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.clock import Clock
from cocotb.decorators import external
from cocotb.utils import get_sim_time

import pytest


def return_two(dut):
    return 2


@cocotb.function
async def await_two_clock_edges(dut):
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    await Timer(1, units='ns')
    dut._log.info("Returning from await_two_clock_edges")
    return 2


def calls_cocotb_function(dut):
    return await_two_clock_edges(dut)


def print_sim_time(dut, base_time):
    # We are not calling out here so time should not advance
    # And should also remain consistent
    for _ in range(5):
        _t = get_sim_time('ns')
        dut._log.info("Time reported = %d", _t)
        assert _t == base_time
    dut._log.info("external function has ended")


@cocotb.test()
async def test_time_in_external(dut):
    """
    Test that the simulation time does not advance if the wrapped external
    routine does not call @function
    """
    await Timer(10, units='ns')
    time = get_sim_time('ns')
    dut._log.info("Time at start of test = %d" % time)
    for i in range(100):
        dut._log.info("Loop call %d" % i)
        await external(print_sim_time)(dut, time)

    time_now = get_sim_time('ns')
    await Timer(10, units='ns')

    assert time == time_now


# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def test_time_in_function(dut):
    """
    Test that an @external function calling back into a cocotb @function
    takes the expected amount of time
    """
    @cocotb.function
    def wait_cycles(dut, n):
        for _ in range(n):
            yield RisingEdge(dut.clk)

    @external
    def wait_cycles_wrapper(dut, n):
        return wait_cycles(dut, n)

    clk_gen = cocotb.fork(Clock(dut.clk, 100, units='ns').start())
    await Timer(10, units='ns')
    for n in range(5):
        for i in range(20):
            await RisingEdge(dut.clk)
            time = get_sim_time('ns')
            expected_after = time + 100*n
            await wait_cycles_wrapper(dut, n)
            time_after = get_sim_time('ns')
            assert expected_after == time_after


# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def test_external_call_return(dut):
    """
    Test ability to await an external function that is not a coroutine using @external
    """
    async def clock_monitor(dut):
        count = 0
        while True:
            await RisingEdge(dut.clk)
            await Timer(1000, units='ns')
            count += 1

    mon = cocotb.fork(clock_monitor(dut))
    clk_gen = cocotb.fork(Clock(dut.clk, 100, units='ns').start())
    value = await external(return_two)(dut)
    assert value == 2


@cocotb.test()
async def test_consecutive_externals(dut):
    """
    Test that multiple @external functions can be called in the same test
    """
    value = await external(return_two)(dut)
    dut._log.info("First one completed")
    assert value == 2

    value = await external(return_two)(dut)
    dut._log.info("Second one completed")
    assert value == 2


@cocotb.test()
async def test_external_from_readonly(dut):
    """
    Test that @external functions that don't consume simulation time
    can be called from ReadOnly state
    """
    await ReadOnly()
    dut._log.info("In readonly")
    value = await external(return_two)(dut)
    assert value == 2


@cocotb.test()
async def test_function_from_readonly(dut):
    """
    Test that @external functions that call @functions that await Triggers
    can be called from ReadOnly state
    """
    clk_gen = cocotb.fork(Clock(dut.clk, 100, units='ns').start())

    await ReadOnly()
    dut._log.info("In readonly")
    value = await external(calls_cocotb_function)(dut)
    assert value == 2


# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def test_function_that_awaits(dut):
    """
    Test that @external functions can call @function coroutines that
    awaits Triggers and return values back through to
    the test
    """
    clk_gen = cocotb.fork(Clock(dut.clk, 100, units='ns').start())

    value = await external(calls_cocotb_function)(dut)
    assert value == 2


# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def test_await_after_function(dut):
    """
    Test that awaiting a Trigger works after returning
    from @external functions that call @functions that consume
    simulation time
    """
    clk_gen = cocotb.fork(Clock(dut.clk, 100, units='ns').start())

    value = await external(calls_cocotb_function)(dut)
    assert value == 2

    await Timer(10, units="ns")
    await RisingEdge(dut.clk)


# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def test_external_from_fork(dut):
    """
    Test that @external functions work when awaited from a forked
    task
    """
    async def run_function(dut):
        value = await external(calls_cocotb_function)(dut)
        return value

    async def run_external(dut):
        value = await external(return_two)(dut)
        return value

    clk_gen = cocotb.fork(Clock(dut.clk, 100, units='ns').start())

    coro1 = cocotb.fork(run_function(dut))
    value = await coro1.join()
    assert value == 2
    dut._log.info("Back from join 1")

    value = 0
    coro2 = cocotb.fork(run_external(dut))
    value = await coro2.join()
    assert value == 2
    dut._log.info("Back from join 2")


@cocotb.test()
async def test_external_raised_exception(dut):
    """
    Test that exceptions thrown by @external functions can be caught
    """
    @external
    def func():
        raise ValueError()

    with pytest.raises(ValueError):
        await func()


@cocotb.test()
async def test_external_returns_exception(dut):
    """
    Test that exceptions can be returned by @external functions
    """
    @external
    def func():
        return ValueError()

    result = await func()

    assert isinstance(result, ValueError)


@cocotb.test()
async def test_function_raised_exception(dut):
    """
    Test that exceptions thrown by @function coroutines can be caught
    """
    @cocotb.function
    async def func():
        raise ValueError()

    @external
    def ext():
        return func()

    with pytest.raises(ValueError):
        await ext()


@cocotb.test()
async def test_function_returns_exception(dut):
    """
    Test that exceptions can be returned by @function coroutines
    """
    @cocotb.function
    def gen_func():
        return ValueError()
        yield

    @external
    def ext():
        return gen_func()

    result = await ext()

    assert isinstance(result, ValueError)


@cocotb.test()
async def test_function_from_weird_thread_fails(dut):
    """
    Test that background threads caling a @function do not hang forever
    """
    func_started = False
    caller_resumed = False
    raised = False

    @cocotb.function
    async def func():
        nonlocal func_started
        func_started = True
        await Timer(10, units='ns')

    def function_caller():
        nonlocal raised
        nonlocal caller_resumed
        try:
            func()
        except RuntimeError:
            raised = True
        finally:
            caller_resumed = True

    @external
    def ext():
        result = []

        t = threading.Thread(target=function_caller)
        t.start()
        t.join()

    task = cocotb.fork(ext())

    await Timer(20, units='ns')

    assert caller_resumed, "Caller was never resumed"
    assert not func_started, "Function should never have started"
    assert raised, "No exception was raised to warn the user"

    await task.join()


@cocotb.test()
async def test_function_called_in_parallel(dut):
    """
    Test that the same `@function` can be called from two parallel background
    threads.
    """
    @cocotb.function
    async def function(x):
        await Timer(1, units='ns')
        return x

    @cocotb.external
    def call_function(x):
        return function(x)

    t1 = cocotb.fork(call_function(1))
    t2 = cocotb.fork(call_function(2))
    v1 = await t1
    v2 = await t2
    assert v1 == 1, v1
    assert v2 == 2, v2
