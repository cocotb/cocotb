# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Test for scheduler and coroutine behavior

* fork
* join
* kill
"""

import cocotb
from cocotb.triggers import Join, Timer, RisingEdge, Trigger, NullTrigger
from cocotb.result import TestFailure
from cocotb.clock import Clock
from test_cocotb import clock_gen


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


@cocotb.test()
def test_stack_overflow(dut):
    """
    Test against stack overflows when starting many coroutines that terminate
    before passing control to the simulator.
    """
    # gh-637
    @cocotb.coroutine
    def null_coroutine():
        yield NullTrigger()

    for _ in range(10000):
        yield null_coroutine()

    yield Timer(100)
