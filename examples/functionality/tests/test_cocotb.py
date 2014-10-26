#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""
A set of tests that demonstrate cocotb functionality

Also used a regression test of cocotb capabilities
"""

import cocotb
from cocotb.triggers import Timer, Join, RisingEdge, ReadOnly, ReadWrite
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure



# Tests relating to providing meaningful errors if we forget to use the
# yield keyword correctly to turn a function into a coroutine

@cocotb.test(expect_fail=True)
def test_not_a_coroutine(dut):
    """Example of a failing to use the yield keyword in a test"""
    dut.log.warning("This test will fail because we don't yield anything")

@cocotb.coroutine
def function_not_a_coroutine():
    """If we don't yield, this isn't a coroutine"""
    return "This should fail"

@cocotb.test(expect_error=True)
def test_function_not_a_coroutine(dut):
    """Example of trying to yield a coroutine that isn't a coroutine"""
    yield Timer(500)
    yield function_not_a_coroutine()

@cocotb.test(expect_error=True)
def test_function_not_a_coroutine_fork(dut):
    """Example of trying to fork a coroutine that isn't a coroutine"""
    yield Timer(500)
    cocotb.fork(function_not_a_coroutine())
    yield Timer(500)

def normal_function(dut):
    return True

@cocotb.test(expect_error=True)
def test_function_not_decorated(dut):
    yield normal_function(dut)

@cocotb.test(expect_fail=False)
def test_function_reentrant_clock(dut):
    """Test yielding a reentrant clock"""
    clock = dut.clk
    timer = Timer(100)
    for i in range(10):
        clock <= 0
        yield timer
        clock <= 1
        yield timer


@cocotb.coroutine
def clock_gen(clock):
    """Example clock gen for test use"""
    for i in range(5):
        clock <= 0
        yield Timer(100)
        clock <= 1
        yield Timer(100)
    clock.log.warning("Clock generator finished!")

@cocotb.test(expect_fail=False)
def test_yield_list(dut):
    """Example of yeilding on a list of triggers"""
    clock = dut.clk;
    cocotb.scheduler.add(clock_gen(clock))
    yield [Timer(1000), Timer(2000)]

    yield Timer(10000)

test_flag = False

@cocotb.coroutine
def clock_yield(generator):
    global test_flag
    yield Join(generator)
    test_flag = True

@cocotb.test(expect_fail=True)
def test_duplicate_yield(dut):
    """A trigger can not be yielded on twice"""

@cocotb.test(expect_fail=False)
def test_coroutine_kill(dut):
    """Test that killing a coroutine causes pending routine continue"""
    global test_flag
    clk_gen = cocotb.scheduler.add(clock_gen(dut.clk))
    yield Timer(100)
    clk_gen_two = cocotb.fork(clock_yield(clk_gen))
    yield Timer(100)
    clk_gen.kill()
    if test_flag is not False:
        raise cocotb.TestFailed
    yield Timer(1000)
    if test_flag is not True:
        raise cocotb.TestFailed

@cocotb.test(expect_error=True)
def test_adding_a_coroutine_without_starting(dut):
    """Catch (and provide useful error) for attempts to fork coroutines incorrectly"""
    yield Timer(100)
    forked = cocotb.fork(clock_gen)
    yield Timer(100)
    yield Join(forked)
    yield Timer(100)

@cocotb.test(expect_fail=False)
def test_anternal_clock(dut):
    """Test ability to yeild on an external non cocotb coroutine decorated function"""
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    count = 0
    while count is not 100:
        yield RisingEdge(dut.clk)
        count += 1
    clk_gen.kill()

exited = False

@cocotb.coroutine
def do_test_readwrite_in_readonly(dut):
    global exited
    yield RisingEdge(dut.clk)
    yield ReadOnly()
    dut.clk <= 0
    yield ReadWrite()
    exited = True

@cocotb.coroutine
def do_test_afterdelay_in_readonly(dut, delay):
    global exited
    yield RisingEdge(dut.clk)
    yield ReadOnly()
    yield Timer(delay)
    exited = True

@cocotb.test(expect_error=True)
def test_readwrite_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    coro = cocotb.fork(do_test_readwrite_in_readonly(dut))
    yield [Join(coro), Timer(10000)]
    clk_gen.kill()
    if exited is not True:
        raise cocotb.TestFailed

@cocotb.test(expect_error=cocotb.SIM_NAME in ["Icarus Verilog"])
def test_afterdelay_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    coro = cocotb.fork(do_test_afterdelay_in_readonly(dut, 0))
    yield [Join(coro), Timer(100000)]
    clk_gen.kill()
    if exited is not True:
        raise cocotb.TestFailed

@cocotb.test()
def test_afterdelay_in_readonly_valid(dut):
    """Same as test_afterdelay_in_readonly but with valid delay > 0"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    coro = cocotb.fork(do_test_afterdelay_in_readonly(dut, 1))
    yield [Join(coro), Timer(100000)]
    clk_gen.kill()
    if exited is not True:
        raise cocotb.TestFailed

@cocotb.coroutine
def clock_one(dut):
    count = 0
    while count is not 50:
        yield RisingEdge(dut.clk)
        yield Timer(1000)
        count += 1

@cocotb.coroutine
def clock_two(dut):
    count = 0
    while count is not 50:
        yield RisingEdge(dut.clk)
        yield Timer(10000)
        count += 1

@cocotb.test(expect_fail=False)
def test_coroutine_close_down(dut):
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    coro_one = cocotb.fork(clock_one(dut))
    coro_two = cocotb.fork(clock_two(dut))

    yield Join(coro_one)
    yield Join(coro_two)

    dut.log.info("Back from joins")

@cocotb.coroutine
def syntax_error():
    yield Timer(100)
    fail

@cocotb.test(expect_error=True)
def test_syntax_error(dut):
    """Syntax error in the test"""
    yield clock_gen(dut.clk)
    fail

@cocotb.test(expect_error=True)
def test_coroutine_syntax_error(dut):
    """Syntax error in a coroutine that we yield"""
    yield clock_gen(dut.clk)
    yield syntax_error()

@cocotb.test(expect_error=True)
def test_fork_syntax_error(dut):
    """Syntax error in a coroutine that we fork"""
    yield clock_gen(dut.clk)
    cocotb.fork(syntax_error())
    yield clock_gen(dut.clk)



@cocotb.coroutine
def count_edges_cycles(signal, edges):
    edge = RisingEdge(signal)
    for i in xrange(edges):
        yield edge
        signal.log.info("Rising edge %d detected" % i)
    signal.log.info("Finished, returning %d" % edges)
    raise ReturnValue(edges)

@cocotb.test()
def test_fork_and_monitor(dut, period=1000, clocks=6):
    cocotb.fork(Clock(dut.clk, period).start())

    # Ensure the clock has started
    yield RisingEdge(dut.clk)

    timer = Timer(period + 10)
    task = cocotb.fork(count_edges_cycles(dut.clk, clocks))
    count = 0
    expect = clocks-1


    while True:
        result = yield [timer, task.join()]
        if count > expect:
            raise TestFailure("Task didn't complete in expected time")
        if result is timer:
            dut.log.info("Count %d: Task still running" % count)
            count += 1
        else:
            break
    if count != expect:
        raise TestFailure("Expected to monitor the task %d times but got %d" % (
                                                             expect, count))
    if result != clocks:
        raise TestFailure("Expected task to return %d but got %s" % (clocks, repr(result)))


