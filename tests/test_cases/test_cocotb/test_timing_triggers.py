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
import re
from decimal import Decimal
from fractions import Fraction

import pytest

import cocotb
from cocotb.clock import Clock
from cocotb.simulator import get_precision
from cocotb.triggers import (
    NextTimeStep,
    ReadOnly,
    ReadWrite,
    RisingEdge,
    SimTimeoutError,
    Timer,
    with_timeout,
)
from cocotb.utils import get_sim_steps, get_sim_time

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()
SIM_NAME = cocotb.SIM_NAME.lower()
if LANGUAGE == "verilog":
    INTF = "vpi"
elif SIM_NAME.startswith("modelsim"):
    INTF = os.environ.get("VHDL_GPI_INTERFACE", "fli")
else:
    INTF = "vhpi"


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
@cocotb.test(skip=(LANGUAGE == "vhdl" and SIM_NAME.startswith(("xmsim", "nvc"))))
async def test_timer_with_units(dut):
    # The following test assumes a time precision of 1ps. Update the simulator
    # invocation if this assert hits!
    assert get_precision() == -12

    time_step = get_sim_time(units="step")

    # Await for one simulator time step
    await Timer(1)  # NOTE: explicitly no units argument here!
    time_step = get_sim_time(units="step") - time_step

    pattern = "Unable to accurately represent .* with the simulator precision of .*"
    with pytest.raises(ValueError, match=pattern):
        await Timer(2.5 * time_step, units="step")
    dut._log.info("As expected, unable to create a timer of 2.5 simulator time steps")

    time_step = get_sim_time(units="step")

    await Timer(3, "ns")

    assert get_sim_time(units="step") == time_step + get_sim_steps(3, "ns")

    time_step = get_sim_time(units="step")
    await Timer(1.5, "ns")

    assert get_sim_time(units="step") == time_step + get_sim_steps(1.5, "ns")

    time_step = get_sim_time(units="step")
    await Timer(10.0, "ps")

    assert get_sim_time(units="step") == time_step + get_sim_steps(10, "ps")

    time_step = get_sim_time(units="step")
    await Timer(1.0, "us")

    assert get_sim_time(units="step") == time_step + get_sim_steps(1, "us")


@cocotb.test()
async def test_timer_with_rational_units(dut):
    """Test that rounding errors are not introduced in exact values"""
    # now with fractions
    time_step = get_sim_time(units="step")
    await Timer(Fraction(1, int(1e9)), units="sec")
    assert get_sim_time(units="step") == time_step + get_sim_steps(1, "ns")

    # now with decimals
    time_step = get_sim_time(units="step")
    await Timer(Decimal("1e-9"), units="sec")
    assert get_sim_time(units="step") == time_step + get_sim_steps(1, "ns")


async def do_test_afterdelay_in_readonly(dut, delay):
    global exited
    await RisingEdge(dut.clk)
    exited = True


@cocotb.test
async def test_cached_write_in_readonly(dut):
    """Test doing invalid sim operation"""
    await ReadOnly()
    with pytest.raises(RuntimeError):
        dut.stream_in_data.value = 0


@cocotb.test
async def test_afterdelay_in_readonly_valid(dut):
    """Test Timer delay after ReadOnly phase"""
    # This *should* fail on VHPI simulators as it is not a legal transition
    # but apparently all simulators support it (gh-3967).
    await ReadOnly()
    await Timer(1, "ns")


@cocotb.test()
async def test_writes_have_taken_effect_after_readwrite(dut):
    """Test that ReadWrite fires first for the background write coro"""
    dut.stream_in_data.value = 0

    async def write_manually():
        await ReadWrite()
        # this should overwrite the write written below
        dut.stream_in_data.value = 2

    # queue a background task to do a manual write
    waiter = cocotb.start_soon(write_manually())

    # do a delayed write. This will be overwritten
    dut.stream_in_data.value = 3
    await waiter

    # check that the write we expected took precedence
    await ReadOnly()
    assert dut.stream_in_data.value == 2


async def example():
    await Timer(10, "ns")
    return 1


@cocotb.test()
async def test_timeout_func_coro_fail(dut):
    with pytest.raises(SimTimeoutError):
        await with_timeout(
            cocotb.start_soon(example()), timeout_time=1, timeout_unit="ns"
        )


@cocotb.test()
async def test_timeout_func_coro_pass(dut):
    res = await with_timeout(
        cocotb.start_soon(example()), timeout_time=100, timeout_unit="ns"
    )
    assert res == 1


@cocotb.test()
async def test_timeout_func_fail(dut):
    with pytest.raises(SimTimeoutError):
        await with_timeout(example(), timeout_time=1, timeout_unit="ns")


@cocotb.test()
async def test_timeout_func_pass(dut):
    res = await with_timeout(example(), timeout_time=100, timeout_unit="ns")
    assert res == 1


@cocotb.test()
async def test_readwrite(dut):
    """Test that ReadWrite can be waited on"""
    # gh-759
    await Timer(1, "ns")
    dut.clk.value = 1
    t = ReadWrite()
    result = await t
    assert isinstance(result, ReadWrite)
    assert result is t


@cocotb.test()
async def test_singleton_isinstance(dut):
    """
    Test that the result of trigger expression have a predictable type
    """
    assert isinstance(NextTimeStep(), NextTimeStep)
    assert isinstance(ReadOnly(), ReadOnly)
    assert isinstance(ReadWrite(), ReadWrite)


@cocotb.test()
async def test_timing_trigger_repr(_):
    nts = NextTimeStep()
    assert repr(nts) == "NextTimeStep()"
    ro = ReadOnly()
    assert repr(ro) == "ReadOnly()"
    rw = ReadWrite()
    assert repr(rw) == "ReadWrite()"
    t = Timer(1)
    assert re.match(
        r"<Timer of \d+\.\d+ps at \w+>",
        repr(t),
    )


@cocotb.test
async def test_neg_timer(_):
    """Test negative timer values are forbidden"""
    with pytest.raises(ValueError):
        Timer(-42)  # no need to even `await`, constructing it is an error
    with pytest.raises(ValueError):
        Timer(0)


@cocotb.test
async def test_timer_rounds_to_0(_) -> None:
    steps = get_sim_time("step")
    await Timer(0.1, "step", round_mode="round")
    assert get_sim_time("step") == steps + 1


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
        await with_timeout(
            Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="error"
        )
    await with_timeout(
        Timer(1, "step"), timeout_time=2, timeout_unit="step", round_mode="error"
    )
    await with_timeout(
        Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="floor"
    )
    await with_timeout(
        Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="ceil"
    )
    await with_timeout(
        Timer(1, "step"), timeout_time=2.5, timeout_unit="step", round_mode="round"
    )


# Riviera VHPI ReadOnly in ValueChange moves to next time step (gh-4119)
@cocotb.test(expect_fail=SIM_NAME.startswith("riviera") and INTF == "vhpi")
async def test_readonly_in_valuechange(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await RisingEdge(dut.clk)
    curr_time = get_sim_time()
    await ReadOnly()
    assert get_sim_time() == curr_time


@cocotb.test
async def test_readonly_in_timer(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await Timer(3, "ns")
    curr_time = get_sim_time()
    await ReadOnly()
    assert get_sim_time() == curr_time


# Riviera VHPI ReadOnly in ReadWrite moves to next time step (gh-4120)
@cocotb.test(expect_fail=SIM_NAME.startswith("riviera") and INTF == "vhpi")
async def test_readonly_in_readwrite(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await RisingEdge(dut.clk)
    curr_time = get_sim_time()
    await ReadWrite()
    assert get_sim_time() == curr_time
    await ReadOnly()
    assert get_sim_time() == curr_time


@cocotb.test
async def test_sim_phase(dut) -> None:
    assert cocotb.sim_phase is cocotb.SimPhase.NORMAL
    await ReadWrite()
    assert cocotb.sim_phase is cocotb.SimPhase.READ_WRITE
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await Timer(10, "ns")
    assert cocotb.sim_phase is cocotb.SimPhase.NORMAL
    await ReadOnly()
    assert cocotb.sim_phase is cocotb.SimPhase.READ_ONLY
    await RisingEdge(dut.clk)
    assert cocotb.sim_phase is cocotb.SimPhase.NORMAL


@cocotb.test
async def test_readwrite_in_readonly(_) -> None:
    await ReadOnly()
    with pytest.raises(RuntimeError):
        await ReadWrite()


@cocotb.test
async def test_readonly_in_readonly(_) -> None:
    await ReadOnly()
    with pytest.raises(RuntimeError):
        await ReadOnly()


@cocotb.test
async def test_next_time_step(_) -> None:
    """Test Timer causes NextTimeStep to wake up after Timer fires."""

    # We can't really test if the NextTimeStep is accurate with this test as a part of
    # the regression. There are many events which will trigger a simulator wakeup. And
    # for the simulators where cancelling triggers does not work and we just mark them
    # as "removed", the next time step caused by them is unavoidable, making this
    # totally non-deterministic. This test really exists only to ensure that the code
    # paths work and the Trigger fires.

    async def wait_ns(time_ns: int) -> None:
        await Timer(time_ns, "ns")

    cocotb.start_soon(wait_ns(10))
    await NextTimeStep()
