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
from cocotb.triggers import Timer, RisingEdge, ReadOnly, ReadWrite, Join, NextTimeStep, First, TriggerException
from cocotb.utils import get_sim_time, get_sim_steps
from cocotb.clock import Clock

from common import assert_raises

from fractions import Fraction
from decimal import Decimal


@cocotb.test()
async def test_function_reentrant_clock(dut):
    """Test awaiting a reentrant clock"""
    clock = dut.clk
    timer = Timer(100, "ns")
    for i in range(10):
        clock <= 0
        await timer
        clock <= 1
        await timer


@cocotb.test()
async def test_timer_with_units(dut):
    time_fs = get_sim_time(units='fs')

    # Await for one simulator time step
    await Timer(1)  # NOTE: explicitly no units argument here!
    time_step = get_sim_time(units='fs') - time_fs

    pattern = "Unable to accurately represent .* with the simulator precision of .*"
    with assert_raises(ValueError, pattern):
        await Timer(2.5*time_step, units='fs')
    dut._log.info("As expected, unable to create a timer of 2.5 simulator time steps")

    time_fs = get_sim_time(units='fs')

    await Timer(3, 'ns')

    assert get_sim_time(units='fs') == time_fs+3_000_000.0, "Expected a delay of 3 ns"

    time_fs = get_sim_time(units='fs')
    await Timer(1.5, 'ns')

    assert get_sim_time(units='fs') == time_fs+1_500_000.0, "Expected a delay of 1.5 ns"

    time_fs = get_sim_time(units='fs')
    await Timer(10.0, 'ps')

    assert get_sim_time(units='fs') == time_fs+10_000.0, "Expected a delay of 10 ps"

    time_fs = get_sim_time(units='fs')
    await Timer(1.0, 'us')

    assert get_sim_time(units='fs') == time_fs+1_000_000_000.0, "Expected a delay of 1 us"


@cocotb.test()
async def test_timer_with_rational_units(dut):
    """ Test that rounding errors are not introduced in exact values """
    # now with fractions
    time_fs = get_sim_time(units='fs')
    await Timer(Fraction(1, int(1e9)), units='sec')
    assert get_sim_time(units='fs') == time_fs + 1_000_000.0, "Expected a delay of 1 ns"

    # now with decimals
    time_fs = get_sim_time(units='fs')
    await Timer(Decimal('1e-9'), units='sec')
    assert get_sim_time(units='fs') == time_fs + 1_000_000.0, "Expected a delay of 1 ns"


exited = False


async def do_test_readwrite_in_readonly(dut):
    global exited
    await RisingEdge(dut.clk)
    await ReadOnly()
    await ReadWrite()
    exited = True


async def do_test_cached_write_in_readonly(dut):
    global exited
    await RisingEdge(dut.clk)
    await ReadOnly()
    dut.clk <= 0
    exited = True


async def do_test_afterdelay_in_readonly(dut, delay):
    global exited
    await RisingEdge(dut.clk)
    await ReadOnly()
    await Timer(delay, "ns")
    exited = True


# Riviera and Questa (in Verilog) correctly fail to register ReadWrite after ReadOnly
# Riviera and Questa (in VHDL) incorrectly allow registering ReadWrite after ReadOnly
@cocotb.test(
    expect_error=TriggerException
    if cocotb.LANGUAGE in ["verilog"]
    and cocotb.SIM_NAME.lower().startswith(("riviera", "modelsim"))
    else (),
    expect_fail=cocotb.SIM_NAME.lower().startswith(
        ("icarus", "ncsim", "xmsim")
    ),
)
async def test_readwrite_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())
    coro = cocotb.fork(do_test_readwrite_in_readonly(dut))
    await First(Join(coro), Timer(10_000, "ns"))
    clk_gen.kill()
    assert exited


@cocotb.test(expect_error=Exception)
async def test_cached_write_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())
    coro = cocotb.fork(do_test_cached_write_in_readonly(dut))
    await First(Join(coro), Timer(10_000, "ns"))
    clk_gen.kill()
    assert exited


@cocotb.test()
async def test_afterdelay_in_readonly_valid(dut):
    """Test Timer delay after ReadOnly phase"""
    global exited
    exited = False
    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())
    coro = cocotb.fork(do_test_afterdelay_in_readonly(dut, 1))
    await First(Join(coro), Timer(100_000, "ns"))
    clk_gen.kill()
    assert exited


@cocotb.test()
async def test_writes_have_taken_effect_after_readwrite(dut):
    """ Test that ReadWrite fires first for the background write coro """
    dut.stream_in_data.setimmediatevalue(0)

    async def write_manually():
        await ReadWrite()
        # this should overwrite the write written below
        dut.stream_in_data.setimmediatevalue(2)

    # queue a background task to do a manual write
    waiter = cocotb.fork(write_manually())

    # do a delayed write. This will be overwritten
    dut.stream_in_data <= 3
    await waiter

    # check that the write we expected took precedence
    await ReadOnly()
    assert dut.stream_in_data.value == 2


@cocotb.coroutine   # cocotb.coroutine necessary to use in with_timeout
async def example():
    await Timer(10, 'ns')
    return 1


@cocotb.test()
async def test_timeout_func_fail(dut):
    try:
        await cocotb.triggers.with_timeout(example(), timeout_time=1, timeout_unit='ns')
    except cocotb.result.SimTimeoutError:
        pass
    else:
        assert False, "Expected a Timeout"


@cocotb.test()
async def test_timeout_func_pass(dut):
    res = await cocotb.triggers.with_timeout(example(), timeout_time=100, timeout_unit='ns')
    assert res == 1


@cocotb.test()
async def test_readwrite(dut):
    """ Test that ReadWrite can be waited on """
    # gh-759
    await Timer(1, "ns")
    dut.clk <= 1
    await ReadWrite()


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


@cocotb.test()
async def test_time_units_eq_None(dut):
    """Test deprecation warning when time units are None"""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Timer(1, units=None)
        assert issubclass(w[-1].category, DeprecationWarning)
        assert 'Using units=None is deprecated, use units="step" instead.' in str(w[-1].message)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Clock(dut.clk, 2, units=None)
        assert issubclass(w[-1].category, DeprecationWarning)
        assert 'Using units=None is deprecated, use units="step" instead.' in str(w[-1].message)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        get_sim_steps(222, units=None)
        assert issubclass(w[-1].category, DeprecationWarning)
        assert 'Using units=None is deprecated, use units="step" instead.' in str(w[-1].message)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        await cocotb.triggers.with_timeout(example(), timeout_time=12_000_000, timeout_unit=None)
        assert issubclass(w[-1].category, DeprecationWarning)
        assert 'Using timeout_unit=None is deprecated, use timeout_unit="step" instead.' in str(w[-1].message)
