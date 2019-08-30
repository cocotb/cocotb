#!/usr/bin/env python

''' Copyright (c) 2013, 2018 Potential Ventures Ltd
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
import logging
import sys
import textwrap
import warnings

"""
A set of tests that demonstrate cocotb functionality

Also used as regression test of cocotb capabilities
"""

import cocotb
from cocotb.triggers import (Timer, Join, RisingEdge, FallingEdge, Edge,
                             ReadOnly, ReadWrite, ClockCycles, NextTimeStep,
                             NullTrigger, Combine, Event, First, Trigger)
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure, TestError, TestSuccess
from cocotb.utils import get_sim_time

from cocotb.binary import BinaryValue
from cocotb import _py_compat

# Tests relating to providing meaningful errors if we forget to use the
# yield keyword correctly to turn a function into a coroutine

@cocotb.test(expect_fail=True)
def test_not_a_coroutine(dut):
    """Example of a failing to use the yield keyword in a test"""
    dut._log.warning("This test will fail because we don't yield anything")


@cocotb.coroutine
def function_not_a_coroutine():
    """If we don't yield, this isn't a coroutine"""
    return "This should fail"


@cocotb.test()
def test_function_not_a_coroutine(dut):
    """Example of trying to yield a coroutine that isn't a coroutine"""
    yield Timer(500)
    try:
        # failure should occur before we even try to yield or fork the coroutine
        coro = function_not_a_coroutine()
    except TypeError as exc:
        assert "isn't a valid coroutine" in str(exc)
    else:
        raise TestFailure


def normal_function(dut):
    return True


@cocotb.test()
def test_function_not_decorated(dut):
    try:
        yield normal_function(dut)
    except TypeError as exc:
        assert "yielded" in str(exc)
        assert "scheduler can't handle" in str(exc)
    except:
        raise TestFailure


@cocotb.test()
def test_function_not_decorated_fork(dut):
    """Example of trying to fork a coroutine that isn't a coroutine"""
    yield Timer(500)
    try:
        cocotb.fork(normal_function(dut))
    except TypeError as exc:
        assert "isn't a coroutine" in str(exc)
    else:
        raise TestFailure()

    yield Timer(500)


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
    clock._log.warning("Clock generator finished!")


@cocotb.test(expect_fail=False)
def test_yield_list(dut):
    """Example of yielding on a list of triggers"""
    clock = dut.clk
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
        raise TestFailure
    yield Timer(1000)
    if test_flag is not True:
        raise TestFailure


@cocotb.test()
def test_adding_a_coroutine_without_starting(dut):
    """Catch (and provide useful error) for attempts to fork coroutines
    incorrectly"""
    yield Timer(100)
    try:
        forked = cocotb.fork(clock_gen)
    except TypeError as exc:
        assert "a coroutine that hasn't started" in str(exc)
    else:
        raise TestFailure

def isclose(a, b, rel_tol=1e-09, abs_tol=0.0):
    """
    Polyfill for math.isclose() (Python 3.5+): floating-point "equal"

    Implementation taken from
    https://www.python.org/dev/peps/pep-0485/#proposed-implementation
    """
    return abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

@cocotb.test(expect_fail=False)
def test_clock_with_units(dut):
    clk_1mhz   = Clock(dut.clk, 1.0, units='us')
    clk_250mhz = Clock(dut.clk, 4.0, units='ns')

    if str(clk_1mhz) != "Clock(1.0 MHz)":
        raise TestFailure("{} != 'Clock(1.0 MHz)'".format(str(clk_1mhz)))
    else:
        dut._log.info('Created clock >{}<'.format(str(clk_1mhz)))

    if str(clk_250mhz) != "Clock(250.0 MHz)":
        raise TestFailure("{} != 'Clock(250.0 MHz)'".format(str(clk_250mhz)))
    else:
        dut._log.info('Created clock >{}<'.format(str(clk_250mhz)))

    clk_gen = cocotb.fork(clk_1mhz.start())

    start_time_ns = get_sim_time(units='ns')

    yield Timer(1)

    yield RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 1000.0):
        raise TestFailure("Expected a period of 1 us")

    start_time_ns = edge_time_ns

    yield RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 1000.0):
        raise TestFailure("Expected a period of 1 us")

    clk_gen.kill()

    clk_gen = cocotb.fork(clk_250mhz.start())

    start_time_ns = get_sim_time(units='ns')

    yield Timer(1)

    yield RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 4.0):
        raise TestFailure("Expected a period of 4 ns")

    start_time_ns = edge_time_ns

    yield RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 4.0):
        raise TestFailure("Expected a period of 4 ns")

    clk_gen.kill()

@cocotb.test(expect_fail=False)
def test_timer_with_units(dut):
    time_fs = get_sim_time(units='fs')

    # Yield for one simulation time step
    yield Timer(1)
    time_step = get_sim_time(units='fs') - time_fs

    try:
        # Yield for 2.5 timesteps, should throw exception
        yield Timer(2.5*time_step, units='fs')
        raise TestFailure("Timers should throw exception if time cannot be achieved with simulator resolution")
    except ValueError:
        dut._log.info("As expected, unable to create a timer of 2.5 simulator time steps")

    time_fs = get_sim_time(units='fs')

    yield Timer(3, "ns")

    if get_sim_time(units='fs') != time_fs+3000000.0:
        raise TestFailure("Expected a delay of 3 ns")

    time_fs = get_sim_time(units='fs')
    yield Timer(1.5, "ns")

    if get_sim_time(units='fs') != time_fs+1500000.0:
        raise TestFailure("Expected a delay of 1.5 ns")

    time_fs = get_sim_time(units='fs')
    yield Timer(10.0, "ps")

    if get_sim_time(units='fs') != time_fs+10000.0:
        raise TestFailure("Expected a delay of 10 ps")

    time_fs = get_sim_time(units='fs')
    yield Timer(1.0, "us")

    if get_sim_time(units='fs') != time_fs+1000000000.0:
        raise TestFailure("Expected a delay of 1 us")


@cocotb.test(expect_fail=False)
def test_anternal_clock(dut):
    """Test ability to yield on an external non cocotb coroutine decorated
    function"""
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
    yield ReadWrite()
    exited = True


@cocotb.coroutine
def do_test_cached_write_in_readonly(dut):
    global exited
    yield RisingEdge(dut.clk)
    yield ReadOnly()
    dut.clk <= 0
    exited = True


@cocotb.coroutine
def do_test_afterdelay_in_readonly(dut, delay):
    global exited
    yield RisingEdge(dut.clk)
    yield ReadOnly()
    yield Timer(delay)
    exited = True


@cocotb.test(expect_error=True,
             expect_fail=cocotb.SIM_NAME.lower().startswith(("icarus",
                                                             "riviera",
                                                             "modelsim",
                                                             "ncsim",
                                                             "xmsim")))
def test_readwrite_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    coro = cocotb.fork(do_test_readwrite_in_readonly(dut))
    yield [Join(coro), Timer(10000)]
    clk_gen.kill()
    if exited is not True:
        raise TestFailure

@cocotb.test(expect_error=True,
             expect_fail=cocotb.SIM_NAME.lower().startswith(("icarus",
                                                             "riviera",
                                                             "modelsim",
                                                             "ncsim",
                                                             "xmsim")))
def test_cached_write_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    coro = cocotb.fork(do_test_cached_write_in_readonly(dut))
    yield [Join(coro), Timer(10000)]
    clk_gen.kill()
    if exited is not True:
        raise TestFailure


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith(("icarus",
                                                             "chronologic simulation vcs")),
             skip=cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim")))
def test_afterdelay_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    coro = cocotb.fork(do_test_afterdelay_in_readonly(dut, 0))
    yield [Join(coro), Timer(1000)]
    clk_gen.kill()
    if exited is not True:
        raise TestFailure


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
        raise TestFailure


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

    dut._log.info("Back from joins")


@cocotb.coroutine
def syntax_error():
    yield Timer(100)
    fail


@cocotb.test(expect_error=True)
def test_syntax_error(dut):
    """Syntax error in the test"""
    yield clock_gen(dut.clk)
    fail


#@cocotb.test(expect_error=True)
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


@cocotb.test()
def test_fork_and_monitor(dut, period=1000, clocks=6):
    cocotb.fork(Clock(dut.clk, period).start())

    # Ensure the clock has started
    yield RisingEdge(dut.clk)

    timer = Timer(period + 10)
    task = cocotb.fork(count_edges_cycles(dut.clk, clocks))
    count = 0
    expect = clocks - 1

    while True:
        result = yield [timer, task.join()]
        if count > expect:
            raise TestFailure("Task didn't complete in expected time")
        if result is timer:
            dut._log.info("Count %d: Task still running" % count)
            count += 1
        else:
            break
    if count != expect:
        raise TestFailure("Expected to monitor the task %d times but got %d" %
                          (expect, count))
    if result != clocks:
        raise TestFailure("Expected task to return %d but got %s" %
                          (clocks, repr(result)))


@cocotb.coroutine
def count_edges_cycles(signal, edges):
    edge = RisingEdge(signal)
    for i in range(edges):
        yield edge
        signal._log.info("Rising edge %d detected" % i)
    signal._log.info("Finished, returning %d" % edges)
    raise ReturnValue(edges)


@cocotb.coroutine
def do_single_edge_check(dut, level):
    """Do test for rising edge"""
    old_value = dut.clk.value.integer
    dut._log.info("Value of %s is %d" % (dut.clk, old_value))
    if old_value is level:
        raise TestError("%s not to %d start with" % (dut.clk, not level))
    if level == 1:
        yield RisingEdge(dut.clk)
    else:
        yield FallingEdge(dut.clk)
    new_value = dut.clk.value.integer
    dut._log.info("Value of %s is %d" % (dut.clk, new_value))
    if new_value is not level:
        raise TestError("%s not %d at end" % (dut.clk, level))


@cocotb.test()
def test_rising_edge(dut):
    """Test that a rising edge can be yielded on"""
    dut.clk <= 0
    yield Timer(1)
    test = cocotb.fork(do_single_edge_check(dut, 1))
    yield Timer(10)
    dut.clk <= 1
    fail_timer = Timer(1000)
    result = yield [fail_timer, test.join()]
    if result is fail_timer:
        raise TestError("Test timed out")


@cocotb.test()
def test_falling_edge(dut):
    """Test that a falling edge can be yielded on"""
    dut.clk <= 1
    yield Timer(1)
    test = cocotb.fork(do_single_edge_check(dut, 0))
    yield Timer(10)
    dut.clk <= 0
    fail_timer = Timer(1000)
    result = yield [fail_timer, test.join()]
    if result is fail_timer:
        raise TestError("Test timed out")


@cocotb.test()
def test_either_edge(dut):
    """Test that either edge can be triggered on"""
    dut.clk <= 0
    yield Timer(1)
    dut.clk <= 1
    yield Edge(dut.clk)
    if dut.clk.value.integer is not 1:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    if dut.clk.value.integer is not 0:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 1
    yield Edge(dut.clk)
    if dut.clk.value.integer is not 1:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    if dut.clk.value.integer is not 0:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 1
    yield Edge(dut.clk)
    if dut.clk.value.integer is not 1:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    if dut.clk.value.integer is not 0:
        raise TestError("Value should be 0")


@cocotb.coroutine
def do_clock(dut, limit, period):
    """Simple clock with a limit"""
    wait_period = period / 2
    while limit:
        yield Timer(wait_period)
        dut.clk <= 0
        yield Timer(wait_period)
        dut.clk <= 1
        limit -= 1


@cocotb.coroutine
def do_edge_count(dut, signal):
    """Count the edges"""
    global edges_seen
    count = 0
    while True:
        yield RisingEdge(signal)
        edges_seen += 1


@cocotb.test()
def test_edge_count(dut):
    """Count the number of edges is as expected"""
    global edges_seen
    edges_seen = 0
    clk_period = 100
    edge_count = 10
    clock = cocotb.fork(do_clock(dut, edge_count, clk_period))
    test = cocotb.fork(do_edge_count(dut, dut.clk))

    yield Timer(clk_period * (edge_count + 1))

    if edge_count is not edges_seen:
        raise TestFailure("Correct edge count failed - saw %d wanted %d" %
                          (edges_seen, edge_count))

class StrCallCounter(object):
    def __init__(self):
        self.str_counter = 0

    def __str__(self):
        self.str_counter += 1
        return "__str__ called %d time(s)" % self.str_counter

@cocotb.test()
def test_logging_with_args(dut):
    counter = StrCallCounter()
    dut._log.setLevel(logging.INFO)  # To avoid logging debug message, to make next line run without error
    dut._log.debug("%s", counter)
    assert counter.str_counter == 0

    dut._log.info("%s", counter)
    assert counter.str_counter == 1

    dut._log.info("No substitution")

    dut._log.warning("Testing multiple line\nmessage")

    yield Timer(100)  # Make it do something with time

@cocotb.test()
def test_clock_cycles(dut):
    """
    Test the ClockCycles Trigger
    """

    clk = dut.clk

    clk_gen = cocotb.fork(Clock(clk, 100).start())

    yield RisingEdge(clk)

    dut._log.info("After one edge")

    yield ClockCycles(clk, 10)

    dut._log.info("After 10 edges")

@cocotb.test()
def test_binary_value(dut):
    """
    Test out the cocotb supplied BinaryValue class for manipulating
    values in a style familiar to rtl coders.
    """

    vec = BinaryValue(value=0, n_bits=16)

    dut._log.info("Checking read access to the n_bits property")
    if vec.n_bits != 16:
        raise TestFailure("n_bits is not set correctly - expected %d, got %d" % (16, vec.n_bits))

    dut._log.info("Checking default endianness is Big Endian.")
    if not vec.big_endian:
        raise TestFailure("The default endianness is Little Endian - was expecting Big Endian.")
    if vec.integer != 0:
        raise TestFailure("Expecting our BinaryValue object to have the value 0.")

    dut._log.info("Checking single index assignment works as expected on a Little Endian BinaryValue.")
    vec = BinaryValue(value=0, bits=16, bigEndian=False)
    if vec.big_endian:
        raise TestFailure("Our BinaryValue object is reporting it is Big Endian - was expecting Little Endian.")
    for x in range(vec.n_bits):
        vec[x] = '1'
        dut._log.info("Trying vec[%s] = 1" % x)
        expected_value = 2**(x+1) - 1
        if vec.integer != expected_value:
            raise TestFailure("Failed on assignment to vec[%s] - expecting %s - got %s" % (x, expected_value, vec.integer))
        if vec[x] != 1:
            raise TestFailure("Failed on index compare on vec[%s] - expecting 1 - got %s" % (x, vec[x]))
        dut._log.info("vec = 'b%s" % vec.binstr)

    dut._log.info("Checking slice assignment works as expected on a Little Endian BinaryValue.")
    if vec.integer != 65535:
        raise TestFailure("Expecting our BinaryValue object to be 65535 after the end of the previous test.")
    vec[7:0] = '00110101'
    if vec.binstr != '1111111100110101':
        raise TestFailure("Set lower 8-bits to 00110101 but read back %s" % vec.binstr)
    if vec[7:0].binstr != '00110101':
        raise TestFailure("Set lower 8-bits to 00110101 but read back %s from vec[7:0]" % vec[7:0].binstr)

    dut._log.info("vec[7:0] = 'b%s" % vec[7:0].binstr)
    dut._log.info("vec[15:8] = 'b%s" % vec[15:8].binstr)
    dut._log.info("vec = 'b%s" % vec.binstr)

    yield Timer(100)  # Make it do something with time


@cocotb.test()
def test_binary_value_compat(dut):
    """
    Test backwards-compatibility wrappers for BinaryValue
    """

    dut._log.info("Checking the renaming of bits -> n_bits")
    vec = BinaryValue(value=0, bits=16)
    if vec.n_bits != 16:
        raise TestFailure("n_bits is not set correctly - expected %d, got %d" % (16, vec.n_bits))

    vec = BinaryValue(0, 16)
    if vec.n_bits != 16:
        raise TestFailure("n_bits is not set correctly - expected %d, got %d" % (16, vec.n_bits))

    try:
        vec = BinaryValue(value=0, bits=16, n_bits=17)
    except TypeError:
        pass
    else:
        raise TestFailure("Expected TypeError when using bits and n_bits at the same time.")

    # Test for the DeprecationWarning when using |bits|
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("error")

        try:
            vec = BinaryValue(value=0, bits=16)
        except DeprecationWarning:
            pass
        else:
            TestFailure("Expected DeprecationWarning when using bits instead of n_bits.")

    yield Timer(100)  # Make it do something with time


@cocotb.test()
def join_finished(dut):
    """
    Test that joining a coroutine that has already been joined gives
    the same result as it did the first time.
    """

    retval = None

    @cocotb.coroutine
    def some_coro():
        yield Timer(1)
        raise ReturnValue(retval)

    coro = cocotb.fork(some_coro())

    retval = 1
    x = yield coro.join()
    assert x == 1

    # joining the second time should give the same result.
    # we change retval here to prove it does not run again
    retval = 2
    x = yield coro.join()
    assert x == 1


@cocotb.test()
def consistent_join(dut):
    """
    Test that joining a coroutine returns the finished value
    """
    @cocotb.coroutine
    def wait_for(clk, cycles):
        rising_edge = RisingEdge(clk)
        for _ in range(cycles):
            yield rising_edge
        raise ReturnValue(3)

    cocotb.fork(Clock(dut.clk, 2000, 'ps').start())

    short_wait = cocotb.fork(wait_for(dut.clk, 10))
    long_wait = cocotb.fork(wait_for(dut.clk, 30))

    yield wait_for(dut.clk, 20)
    a = yield short_wait.join()
    b = yield long_wait.join()
    assert a == b == 3


@cocotb.test()
def test_kill_twice(dut):
    """
    Test that killing a coroutine that has already been killed does not crash
    """
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    yield Timer(1)
    clk_gen.kill()
    yield Timer(1)
    clk_gen.kill()


@cocotb.test()
def test_join_identity(dut):
    """
    Test that Join() returns the same object each time
    """
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    assert Join(clk_gen) is Join(clk_gen)
    yield Timer(1)
    clk_gen.kill()


@cocotb.test()
def test_edge_identity(dut):
    """
    Test that Edge triggers returns the same object each time
    """

    re = RisingEdge(dut.clk)
    fe = FallingEdge(dut.clk)
    e = Edge(dut.clk)

    assert re is RisingEdge(dut.clk)
    assert fe is FallingEdge(dut.clk)
    assert e is Edge(dut.clk)

    # check they are all unique
    assert len({re, fe, e}) == 3
    yield Timer(1)


@cocotb.test()
def test_singleton_isinstance(dut):
    """
    Test that the result of trigger expression have a predictable type
    """
    assert isinstance(RisingEdge(dut.clk), RisingEdge)
    assert isinstance(FallingEdge(dut.clk), FallingEdge)
    assert isinstance(Edge(dut.clk), Edge)
    assert isinstance(NextTimeStep(), NextTimeStep)
    assert isinstance(ReadOnly(), ReadOnly)
    assert isinstance(ReadWrite(), ReadWrite)

    yield Timer(1)


@cocotb.test()
def test_lessthan_raises_error(dut):
    """
    Test that trying to use <= as if it were a comparison produces an error
    """
    ret = dut.stream_in_data <= 0x12
    try:
        bool(ret)
    except TypeError:
        pass
    else:
        raise TestFailure(
            "No exception was raised when confusing comparison with assignment"
        )

    # to make this a generator
    if False: yield


@cocotb.test()
def test_tests_are_tests(dut):
    """
    Test that things annotated with cocotb.test are tests
    """
    yield Timer(1)

    assert isinstance(test_tests_are_tests, cocotb.test)


if sys.version_info[:2] >= (3, 3):
    # this would be a syntax error in older python, so we do the whole
    # thing inside exec
    _py_compat.exec_(textwrap.dedent('''
    @cocotb.test()
    def test_coroutine_return(dut):
        """ Test that the Python 3.3 syntax for returning from generators works """
        @cocotb.coroutine
        def return_it(x):
            return x

            # this makes `return_it` a coroutine
            yield

        ret = yield return_it(42)
        if ret != 42:
            raise TestFailure("Return statement did not work")
    '''))


@cocotb.test()
def test_exceptions(dut):
    @cocotb.coroutine
    def raise_soon():
        yield Timer(10)
        raise ValueError('It is soon now')

    try:
        yield raise_soon()
    except ValueError:
        pass
    else:
        raise TestFailure("Exception was not raised")

@cocotb.test()
def test_stack_overflow(dut):
    """
    Test against stack overflows when starting many coroutines that terminate
    before passing control to the simulator.
    """
    @cocotb.coroutine
    def null_coroutine():
        yield NullTrigger()

    for _ in range(10000):
        yield null_coroutine()

    yield Timer(100)


@cocotb.test()
def test_immediate_test(dut):
    """ Test that tests can return immediately """
    return
    yield


@cocotb.test()
def test_immediate_coro(dut):
    """
    Test that coroutines can return immediately
    """
    @cocotb.coroutine
    def immediate_value():
        raise ReturnValue(42)
        yield

    @cocotb.coroutine
    def immediate_exception():
        raise ValueError
        yield

    assert (yield immediate_value()) == 42

    try:
        yield immediate_exception()
    except ValueError:
        pass
    else:
        raise TestFailure("Exception was not raised")


@cocotb.test()
def test_combine(dut):
    """ Test the Combine trigger. """
    # gh-852

    @cocotb.coroutine
    def do_something(delay):
        yield Timer(delay)

    crs = [cocotb.fork(do_something(dly)) for dly in [10, 30, 20]]

    yield Combine(*(cr.join() for cr in crs))


@cocotb.test()
def test_clock_cycles_forked(dut):
    """ Test that ClockCycles can be used in forked coroutines """
    # gh-520

    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    @cocotb.coroutine
    def wait_ten():
        yield ClockCycles(dut.clk, 10)

    a = cocotb.fork(wait_ten())
    b = cocotb.fork(wait_ten())
    yield a.join()
    yield b.join()


@cocotb.test()
def test_yield_list_stale(dut):
    """ Test that a trigger yielded as part of a list can't cause a spurious wakeup """
    # gh-843
    events = [Event() for i in range(3)]

    waiters = [e.wait() for e in events]

    @cocotb.coroutine
    def wait_for_lists():
        ret_i = waiters.index((yield [waiters[0], waiters[1]]))
        assert ret_i == 0, "Expected event 0 to fire, not {}".format(ret_i)

        ret_i = waiters.index((yield [waiters[2]]))
        assert ret_i == 2, "Expected event 2 to fire, not {}".format(ret_i)

    @cocotb.coroutine
    def wait_for_e1():
        """ wait on the event that didn't wake `wait_for_lists` """
        ret_i = waiters.index((yield waiters[1]))
        assert ret_i == 1, "Expected event 1 to fire, not {}".format(ret_i)

    @cocotb.coroutine
    def fire_events():
        """ fire the events in order """
        for e in events:
            yield Timer(1)
            e.set()

    fire_task = cocotb.fork(fire_events())
    e1_task = cocotb.fork(wait_for_e1())
    yield wait_for_lists()

    # make sure the other tasks finish
    yield fire_task.join()
    yield e1_task.join()


@cocotb.test()
def test_nested_first(dut):
    """ Test that nested First triggers behave as expected """
    events = [Event() for i in range(3)]
    waiters = [e.wait() for e in events]

    @cocotb.coroutine
    def fire_events():
        """ fire the events in order """
        for e in events:
            yield Timer(1)
            e.set()


    @cocotb.coroutine
    def wait_for_nested_first():
        inner_first = First(waiters[0], waiters[1])
        ret = yield First(inner_first, waiters[2])

        # should unpack completely, rather than just by one level
        assert ret is not inner_first
        assert ret is waiters[0]

    fire_task = cocotb.fork(fire_events())
    yield wait_for_nested_first()
    yield fire_task.join()


@cocotb.test()
def test_readwrite(dut):
    """ Test that ReadWrite can be waited on """
    # gh-759
    yield Timer(1)
    dut.clk <= 1
    yield ReadWrite()


@cocotb.test()
def test_writes_have_taken_effect_after_readwrite(dut):
    """ Test that ReadWrite fires first for the background write coro """
    dut.stream_in_data.setimmediatevalue(0)

    @cocotb.coroutine
    def write_manually():
        yield ReadWrite()
        # this should overwrite the write written below
        dut.stream_in_data.setimmediatevalue(2)

    # queue a backround task to do a manual write
    waiter = cocotb.fork(write_manually())

    # do a delayed write. This will be overwritten
    dut.stream_in_data <= 3
    yield waiter

    # check that the write we expected took precedence
    yield ReadOnly()
    assert dut.stream_in_data.value == 2


@cocotb.test()
def test_trigger_with_failing_prime(dut):
    """ Test that a trigger failing to prime throws """
    class ABadTrigger(Trigger):
        def prime(self, callback):
            raise RuntimeError("oops")

    yield Timer(1)
    try:
        yield ABadTrigger()
    except RuntimeError as exc:
        assert "oops" in str(exc)
    else:
        raise TestFailure


if sys.version_info[:2] >= (3, 5):
    from test_cocotb_35 import *
