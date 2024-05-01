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

import os
import warnings
from decimal import Decimal
from fractions import Fraction

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.simulator import get_precision
from cocotb.triggers import (
    First,
    Join,
    NextTimeStep,
    ReadOnly,
    ReadWrite,
    RisingEdge,
    Timer,
)
from cocotb.triggers import _TriggerException as TriggerException
from cocotb.utils import get_sim_time

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test()
async def test_function_reentrant_clock(dut):
    """Test awaiting a reentrant clock"""
    clock = dut.clk
    timer = Timer(100, "ns")
    for i in range(10):
        clock.value = 0
        await timer
        clock.value = 1
        await timer


# Xcelium/VHDL does not correctly report the simulator precision.
# See also https://github.com/cocotb/cocotb/issues/3419
# NVC does not support setting precision and always uses 1 fs
# (https://github.com/nickg/nvc/issues/607).
@cocotb.test(
    skip=(LANGUAGE == "vhdl" and cocotb.SIM_NAME.lower().startswith(("xmsim", "nvc")))
)
async def test_timer_with_units(dut):
    # The following test assumes a time precision of 1ps. Update the simulator
    # invocation if this assert hits!
    assert get_precision() == -12

    time_fs = get_sim_time(units="fs")

    # Await for one simulator time step
    await Timer(1)  # NOTE: explicitly no units argument here!
    time_step = get_sim_time(units="fs") - time_fs

    pattern = "Unable to accurately represent .* with the simulator precision of .*"
    with pytest.raises(ValueError, match=pattern):
        await Timer(2.5 * time_step, units="fs")
    dut._log.info("As expected, unable to create a timer of 2.5 simulator time steps")

    time_fs = get_sim_time(units="fs")

    await Timer(3, "ns")

    assert get_sim_time(units="fs") == time_fs + 3_000_000.0, "Expected a delay of 3 ns"

    time_fs = get_sim_time(units="fs")
    await Timer(1.5, "ns")

    assert (
        get_sim_time(units="fs") == time_fs + 1_500_000.0
    ), "Expected a delay of 1.5 ns"

    time_fs = get_sim_time(units="fs")
    await Timer(10.0, "ps")

    assert get_sim_time(units="fs") == time_fs + 10_000.0, "Expected a delay of 10 ps"

    time_fs = get_sim_time(units="fs")
    await Timer(1.0, "us")

    assert (
        get_sim_time(units="fs") == time_fs + 1_000_000_000.0
    ), "Expected a delay of 1 us"


@cocotb.test()
async def test_timer_with_rational_units(dut):
    """Test that rounding errors are not introduced in exact values"""
    # now with fractions
    time_fs = get_sim_time(units="fs")
    await Timer(Fraction(1, int(1e9)), units="sec")
    assert get_sim_time(units="fs") == time_fs + 1_000_000.0, "Expected a delay of 1 ns"

    # now with decimals
    time_fs = get_sim_time(units="fs")
    await Timer(Decimal("1e-9"), units="sec")
    assert get_sim_time(units="fs") == time_fs + 1_000_000.0, "Expected a delay of 1 ns"


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
    dut.clk.value = 0
    exited = True


async def do_test_afterdelay_in_readonly(dut, delay):
    global exited
    await RisingEdge(dut.clk)
    await ReadOnly()
    await Timer(delay, "ns")
    exited = True


# A TriggerException is expected to happen in this test, which indicates that
# ReadWrite after ReadOnly fails to register.
# - Riviera and Questa (in Verilog) and Xcelium pass.
# - Riviera and Questa (in VHDL) incorrectly allow registering ReadWrite
#   after ReadOnly.
# - Xcelium passes (VHDL and Verilog).
@cocotb.test(
    expect_error=TriggerException
    if (
        (
            LANGUAGE in ["verilog"]
            and cocotb.SIM_NAME.lower().startswith(("riviera", "modelsim"))
        )
        or cocotb.SIM_NAME.lower().startswith("xmsim")
    )
    else (),
    expect_fail=cocotb.SIM_NAME.lower().startswith(("icarus", "ncsim")),
)
async def test_readwrite_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    coro = cocotb.start_soon(do_test_readwrite_in_readonly(dut))
    await First(Join(coro), Timer(10_000, "ns"))
    clk_gen.kill()
    assert exited


@cocotb.test(skip=True)
async def test_cached_write_in_readonly(dut):
    """Test doing invalid sim operation"""
    global exited
    exited = False
    clk_gen = cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    coro = cocotb.start_soon(do_test_cached_write_in_readonly(dut))
    await First(Join(coro), Timer(10_000, "ns"))
    clk_gen.kill()
    assert exited


@cocotb.test()
async def test_afterdelay_in_readonly_valid(dut):
    """Test Timer delay after ReadOnly phase"""
    global exited
    exited = False
    clk_gen = cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    coro = cocotb.start_soon(do_test_afterdelay_in_readonly(dut, 1))
    await First(Join(coro), Timer(100_000, "ns"))
    clk_gen.kill()
    assert exited


@cocotb.test()
async def test_writes_have_taken_effect_after_readwrite(dut):
    """Test that ReadWrite fires first for the background write coro"""
    dut.stream_in_data.setimmediatevalue(0)

    async def write_manually():
        await ReadWrite()
        # this should overwrite the write written below
        dut.stream_in_data.setimmediatevalue(2)

    # queue a background task to do a manual write
    waiter = cocotb.start_soon(write_manually())

    # do a delayed write. This will be overwritten
    dut.stream_in_data.value = 3
    await waiter

    # check that the write we expected took precedence
    await ReadOnly()
    assert dut.stream_in_data.value == 2


async def example_coro():
    await Timer(10, "ns")
    return 1


@cocotb.test()
async def test_timeout_func_coro_fail(dut):
    with pytest.raises(cocotb.result.SimTimeoutError):
        await cocotb.triggers.with_timeout(
            example_coro(), timeout_time=1, timeout_unit="ns"
        )


@cocotb.test()
async def test_timeout_func_coro_pass(dut):
    res = await cocotb.triggers.with_timeout(
        example_coro(), timeout_time=100, timeout_unit="ns"
    )
    assert res == 1


async def example():
    await Timer(10, "ns")
    return 1


@cocotb.test()
async def test_timeout_func_fail(dut):
    with pytest.raises(cocotb.result.SimTimeoutError):
        await cocotb.triggers.with_timeout(example(), timeout_time=1, timeout_unit="ns")


@cocotb.test()
async def test_timeout_func_pass(dut):
    res = await cocotb.triggers.with_timeout(
        example(), timeout_time=100, timeout_unit="ns"
    )
    assert res == 1


@cocotb.test()
async def test_readwrite(dut):
    """Test that ReadWrite can be waited on"""
    # gh-759
    await Timer(1, "ns")
    dut.clk.value = 1
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
    with pytest.raises(ValueError):
        Timer(-42)  # no need to even `await`, constructing it is an error
    # handle 0 special case
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        Timer(0)
        assert (
            "Timer setup with value 0, which might exhibit undefined behavior in some simulators"
            in str(w[-1].message)
        )
        assert issubclass(w[-1].category, RuntimeWarning)


@cocotb.test()
async def test_timer_round_mode(_):
    # test invalid round_mode specifier
    with pytest.raises(ValueError, match="^Invalid round_mode specifier: notvalid"):
        Timer(1, "step", round_mode="notvalid")

    # test default, update if default changes
    with pytest.raises(ValueError):
        Timer(0.5, "step")

    # test valid
    with pytest.raises(ValueError):
        Timer(0.5, "step", round_mode="error")
    assert Timer(24.0, "step", round_mode="error")._sim_steps == 24
    assert Timer(1.2, "step", round_mode="floor")._sim_steps == 1
    assert Timer(1.2, "step", round_mode="ceil")._sim_steps == 2
    assert Timer(1.2, "step", round_mode="round")._sim_steps == 1

    # test with_timeout round_mode
    with pytest.raises(ValueError):
        await cocotb.triggers.with_timeout(
            Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="error"
        )
    await cocotb.triggers.with_timeout(
        Timer(1, "step"), timeout_time=2, timeout_unit="step", round_mode="error"
    )
    await cocotb.triggers.with_timeout(
        Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="floor"
    )
    await cocotb.triggers.with_timeout(
        Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="ceil"
    )
    await cocotb.triggers.with_timeout(
        Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="round"
    )
