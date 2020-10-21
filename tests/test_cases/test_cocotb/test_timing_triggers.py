# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests related to timing triggers

* Timer
* ReadWrite
* ReadOnly
* NextTimeStep
* with_timeout
"""
import cocotb
import warnings
from cocotb.triggers import Timer, RisingEdge, ReadOnly, ReadWrite, Join, NextTimeStep, TriggerException
from cocotb.utils import get_sim_time
from cocotb.result import TestFailure
from cocotb.clock import Clock

from common import assert_raises

from fractions import Fraction
from decimal import Decimal


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
             skip=cocotb.LANGUAGE in ["vhdl"] and cocotb.SIM_NAME.lower().startswith(("riviera")),  # gh-1245
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


@cocotb.test()
def test_afterdelay_in_readonly_valid(dut):
    """Test Timer delay after ReadOnly phase"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    coro = cocotb.fork(do_test_afterdelay_in_readonly(dut, 1))
    yield [Join(coro), Timer(100000)]
    clk_gen.kill()
    if exited is not True:
        raise TestFailure


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


@cocotb.test()
def test_readwrite(dut):
    """ Test that ReadWrite can be waited on """
    # gh-759
    yield Timer(1)
    dut.clk <= 1
    yield ReadWrite()


@cocotb.test()
async def test_singleton_isinstance(dut):
    """
    Test that the result of trigger expression have a predictable type
    """
    assert isinstance(NextTimeStep(), NextTimeStep)
    assert isinstance(ReadOnly(), ReadOnly)
    assert isinstance(ReadWrite(), ReadWrite)


@cocotb.test()
async def test_neg_timer(dut):
    """Test negative timer values are forbidden"""
    with assert_raises(TriggerException):
        Timer(-42)  # no need to even `await`, constructing it is an error
    # handle 0 special case
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Timer(0)
        assert "Timer setup with value 0, which might exhibit undefined behavior in some simulators" in str(w[-1].message)
        assert issubclass(w[-1].category, RuntimeWarning)
