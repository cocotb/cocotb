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

import logging
import re
import textwrap
import traceback
from fractions import Fraction
from decimal import Decimal
from math import isclose

"""
A set of tests that demonstrate cocotb functionality

Also used as regression test of cocotb capabilities
"""

import cocotb
from cocotb.triggers import (Timer, Join, RisingEdge, FallingEdge, Edge,
                             ReadOnly, ReadWrite, ClockCycles, NextTimeStep,
                             NullTrigger, Combine, Event, First, Trigger, Lock)
from cocotb.clock import Clock
from cocotb.result import TestFailure, TestError
from cocotb.utils import get_sim_time
from cocotb.outcomes import Value, Error


# Tests relating to providing meaningful errors if we forget to use the
# yield keyword correctly to turn a function into a coroutine

@cocotb.test(expect_error=TypeError)
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

@cocotb.test()
def test_timer_with_rational_units(dut):
    """ Test that rounding errors are not introduced in exact values """
    # now with fractions
    time_fs = get_sim_time(units='fs')
    yield Timer(Fraction(1, int(1e9)), units='sec')
    assert get_sim_time(units='fs') == time_fs + 1000000.0, "Expected a delay of 1 ns"

    # now with decimals
    time_fs = get_sim_time(units='fs')
    yield Timer(Decimal('1e-9'), units='sec')
    assert get_sim_time(units='fs') == time_fs + 1000000.0, "Expected a delay of 1 ns"


@cocotb.test(expect_fail=False)
def test_anternal_clock(dut):
    """Test ability to yield on an external non cocotb coroutine decorated
    function"""
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    count = 0
    while count != 100:
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
    while count != 50:
        yield RisingEdge(dut.clk)
        yield Timer(1000)
        count += 1


@cocotb.coroutine
def clock_two(dut):
    count = 0
    while count != 50:
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
    return edges


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
    if dut.clk.value.integer != 1:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    if dut.clk.value.integer != 0:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 1
    yield Edge(dut.clk)
    if dut.clk.value.integer != 1:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    if dut.clk.value.integer != 0:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 1
    yield Edge(dut.clk)
    if dut.clk.value.integer != 1:
        raise TestError("Value should be 0")
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    if dut.clk.value.integer != 0:
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

    # now try again on the root cocotb logger, which unlike nested loggers
    # is captured
    counter = StrCallCounter()
    cocotb.log.info("%s", counter)
    assert counter.str_counter == 2  # once for stdout, once for captured logs

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
def join_finished(dut):
    """
    Test that joining a coroutine that has already been joined gives
    the same result as it did the first time.
    """

    retval = None

    @cocotb.coroutine
    def some_coro():
        yield Timer(1)
        return retval

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
        return 3

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


@cocotb.coroutine
def _check_traceback(running_coro, exc_type, pattern):
    try:
        yield running_coro
    except exc_type:
        tb_text = traceback.format_exc()
    else:
        raise TestFailure("Exception was not raised")

    if not re.match(pattern, tb_text):
        raise TestFailure(
            (
                "Traceback didn't match - got:\n\n"
                "{}\n"
                "which did not match the pattern:\n\n"
                "{}"
            ).format(tb_text, pattern)
        )


@cocotb.test()
def test_exceptions_direct(dut):
    """ Test exception propagation via a direct yield statement """
    @cocotb.coroutine
    def raise_inner():
        yield Timer(10)
        raise ValueError('It is soon now')

    @cocotb.coroutine
    def raise_soon():
        yield Timer(1)
        yield raise_inner()

    # it's ok to change this value if the traceback changes - just make sure
    # that when changed, it doesn't become harder to read.
    expected = textwrap.dedent(r"""
    Traceback \(most recent call last\):
      File ".*test_cocotb\.py", line \d+, in _check_traceback
        yield running_coro
      File ".*test_cocotb\.py", line \d+, in raise_soon
        yield raise_inner\(\)
      File ".*test_cocotb\.py", line \d+, in raise_inner
        raise ValueError\('It is soon now'\)
    ValueError: It is soon now""").strip()

    yield _check_traceback(raise_soon(), ValueError, expected)


@cocotb.test()
def test_exceptions_forked(dut):
    """ Test exception propagation via cocotb.fork """
    @cocotb.coroutine
    def raise_inner():
        yield Timer(10)
        raise ValueError('It is soon now')

    @cocotb.coroutine
    def raise_soon():
        yield Timer(1)
        coro = cocotb.fork(raise_inner())
        yield coro.join()

    # it's ok to change this value if the traceback changes - just make sure
    # that when changed, it doesn't become harder to read.
    expected = textwrap.dedent(r"""
    Traceback \(most recent call last\):
      File ".*test_cocotb\.py", line \d+, in _check_traceback
        yield running_coro
      File ".*test_cocotb\.py", line \d+, in raise_soon
        yield coro\.join\(\)
      File ".*test_cocotb\.py", line \d+, in raise_inner
        raise ValueError\('It is soon now'\)
    ValueError: It is soon now""").strip()

    yield _check_traceback(raise_soon(), ValueError, expected)


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
        return 42
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


@cocotb.test(expect_fail=True)
def test_assertion_is_failure(dut):
    yield Timer(1)
    assert False


class MyException(Exception):
    pass


@cocotb.test(expect_error=MyException)
def test_expect_particular_exception(dut):
    yield Timer(1)
    raise MyException()


@cocotb.test(expect_error=(MyException, ValueError))
def test_expect_exception_list(dut):
    yield Timer(1)
    raise MyException()


@cocotb.coroutine
def example():
    yield Timer(10, 'ns')
    return 1


@cocotb.test()
def test_timeout_func_fail(dut):
    try:
        yield cocotb.triggers.with_timeout(example(), timeout_time=1, timeout_unit='ns')
    except cocotb.result.SimTimeoutError:
        pass
    else:
        assert False, "Expected a Timeout"


@cocotb.test()
def test_timeout_func_pass(dut):
    res = yield cocotb.triggers.with_timeout(example(), timeout_time=100, timeout_unit='ns')
    assert res == 1


@cocotb.test(expect_error=cocotb.result.SimTimeoutError, timeout_time=1, timeout_unit='ns')
def test_timeout_testdec_fail(dut):
    yield Timer(10, 'ns')


@cocotb.test(timeout_time=100, timeout_unit='ns')
def test_timeout_testdec_pass(dut):
    yield Timer(10, 'ns')


@cocotb.test(timeout_time=10, timeout_unit='ns')
def test_timeout_testdec_simultaneous(dut):
    try:
        yield cocotb.triggers.with_timeout(Timer(1, 'ns'), timeout_time=1, timeout_unit='ns')
    except cocotb.result.SimTimeoutError:
        pass
    else:
        assert False, "Expected a Timeout"
    # Whether this test fails or passes depends on the behavior of the
    # scheduler, simulator, and the implementation of the timeout function.
    # CAUTION: THIS MAY CHANGE


@cocotb.test()
def test_bad_attr(dut):
    yield cocotb.triggers.NullTrigger()
    try:
        _ = dut.stream_in_data.whoops
    except AttributeError as e:
        assert 'whoops' in str(e)
    else:
        assert False, "Expected AttributeError"


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
async def test_async_from_async(dut):
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


# strings are not supported on Icarus
@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith("icarus"))
async def test_string_handle_takes_bytes(dut):
    dut.string_input_port.value = b"bytes"
    await cocotb.triggers.Timer(10, 'ns')
    val = dut.string_input_port.value
    assert isinstance(val, bytes)
    assert val == b"bytes"
