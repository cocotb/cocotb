#!/usr/bin/env python

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
from cocotb.result import TestFailure
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.clock import Clock
from cocotb.decorators import external
from cocotb.utils import get_sim_time


# Tests relating to calling convention and operation

def return_two(dut):
    # dut._log.info("Sleeping")
    return 2


@cocotb.function
def yield_to_readwrite(dut):
    yield RisingEdge(dut.clk)
    dut._log.info("Returning from yield_to_readwrite")
    yield RisingEdge(dut.clk)
    dut._log.info("Returning from yield_to_readwrite")
    yield Timer(1, "ns")
    return 2


def calls_cocotb_function(dut):
    return yield_to_readwrite(dut)


def print_sim_time(dut, base_time):
    # We are not calling out here so time should not advance
    # And should also remain consistent
    for _ in range(5):
        _t = get_sim_time('ns')
        dut._log.info("Time reported = %d", _t)
        if _t != base_time:
            raise TestFailure("Time reported does not match base_time %f != %f" %
                              (_t, base_time))
    dut._log.info("external function has ended")


@cocotb.coroutine
def clock_monitor(dut):
    count = 0
    while True:
        yield RisingEdge(dut.clk)
        yield Timer(1000)
        count += 1


@cocotb.test()
def test_time_in_external(dut):
    """Test that the simulation time does not advance if the wrapped external
    routine does not itself yield"""
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    yield Timer(10, 'ns')
    time = get_sim_time('ns')
    dut._log.info("Time at start of test = %d" % time)
    for i in range(100):
        dut._log.info("Loop call %d" % i)
        yield external(print_sim_time)(dut, time)

    time_now = get_sim_time('ns')
    yield Timer(10, 'ns')

    if time != time_now:
        raise TestFailure("Time has elapsed over external call")


@cocotb.function
def wait_cycles(dut, n):
    for _ in range(n):
        yield RisingEdge(dut.clk)


def wait_cycles_wrapper(dut, n):
    return wait_cycles(dut, n)

# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else False)
def test_time_in_external_yield(dut):
    """Test that an external function calling back into a cocotb function
    takes the expected amount of time"""
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    yield Timer(10, 'ns')
    for n in range(5):
        for i in range(20):
            yield RisingEdge(dut.clk)
            time = get_sim_time()
            expected_after = time + 100*n
            yield external(wait_cycles_wrapper)(dut, n)
            time_after = get_sim_time()
            if expected_after != time_after:
                raise TestFailure("Wrong time elapsed in external call")

# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else False)
def test_ext_call_return(dut):
    """Test ability to yield on an external non cocotb coroutine decorated
    function"""
    mon = cocotb.scheduler.queue(clock_monitor(dut))
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    value = yield external(return_two)(dut)
    assert value == 2


@cocotb.test()
def test_multiple_externals(dut):
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    value = yield external(return_two)(dut)
    dut._log.info("First one completed")
    assert value == 2

    value = yield external(return_two)(dut)
    dut._log.info("Second one completed")
    assert value == 2


@cocotb.test()
def test_external_from_readonly(dut):
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    yield ReadOnly()
    dut._log.info("In readonly")
    value = yield external(return_two)(dut)
    assert value == 2

# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else False)
def test_external_that_yields(dut):
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    value = yield external(calls_cocotb_function)(dut)
    assert value == 2

# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else False)
def test_external_and_continue(dut):
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    value = yield external(calls_cocotb_function)(dut)
    assert value == 2

    yield Timer(10, "ns")
    yield RisingEdge(dut.clk)


@cocotb.coroutine
def run_external(dut):
    value = yield external(calls_cocotb_function)(dut)
    return value

# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else False)
def test_external_from_fork(dut):
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    coro = cocotb.fork(run_external(dut))
    value = yield coro.join()
    assert value == 2

    dut._log.info("Back from join")


@cocotb.test(expect_fail=True, skip=True)
def test_ext_exit_error(dut):
    """Test that a premature exit of the sim at its request still results in
    the clean close down of the sim world"""
    yield external(return_two)(dut)
    yield Timer(1000)


@cocotb.test()
def test_external_raised_exception(dut):
    """ Test that exceptions thrown by @external functions can be caught """
    # workaround for gh-637
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    @external
    def func():
        raise ValueError()

    try:
        yield func()
    except ValueError:
        pass
    else:
        raise TestFailure('Exception was not thrown')


@cocotb.test()
def test_external_returns_exception(dut):
    """ Test that exceptions can be returned by @external functions """
    # workaround for gh-637
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    @external
    def func():
        return ValueError()

    try:
        result = yield func()
    except ValueError:
        raise TestFailure('Exception should not have been thrown')

    if not isinstance(result, ValueError):
        raise TestFailure('Exception was not returned')


@cocotb.test()
def test_function_raised_exception(dut):
    """ Test that exceptions thrown by @function coroutines can be caught """
    # workaround for gh-637
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    @cocotb.function
    def func():
        raise ValueError()
        yield

    @external
    def ext():
        return func()

    try:
        yield ext()
    except ValueError:
        pass
    else:
        raise TestFailure('Exception was not thrown')


@cocotb.test()
def test_function_returns_exception(dut):
    """ Test that exceptions can be returned by @function coroutines """
    # workaround for gh-637
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    @cocotb.function
    def func():
        return ValueError()
        yield

    @external
    def ext():
        return func()

    try:
        result = yield ext()
    except ValueError:
        raise TestFailure('Exception should not have been thrown')

    if not isinstance(result, ValueError):
        raise TestFailure('Exception was not returned')


@cocotb.test()
def test_function_from_weird_thread_fails(dut):
    """
    Test that background threads caling a @function do not hang forever
    """
    # workaround for gh-637
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    func_started = False
    caller_resumed = False
    raised = False

    @cocotb.function
    def func():
        nonlocal func_started
        func_started = True
        yield Timer(10)

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

    yield Timer(20)

    assert caller_resumed, "Caller was never resumed"
    assert not func_started, "Function should never have started"
    assert raised, "No exception was raised to warn the user"

    yield task.join()


@cocotb.test()
def test_function_called_in_parallel(dut):
    """
    Test that the same `@function` can be called from two parallel background
    threads.
    """
    # workaround for gh-637
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    @cocotb.function
    def function(x):
        yield Timer(1)
        return x

    @cocotb.external
    def call_function(x):
        return function(x)

    t1 = cocotb.fork(call_function(1))
    t2 = cocotb.fork(call_function(2))
    v1 = yield t1
    v2 = yield t2
    assert v1 == 1, v1
    assert v2 == 2, v2
