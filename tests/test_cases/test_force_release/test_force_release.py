# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Tests the Force/Freeze/Release features."""

from __future__ import annotations

import os

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, Timer
from cocotb_tools.sim_versions import GhdlVersion, RivieraVersion

SIM_NAME = cocotb.SIM_NAME.lower()
SIM_VERSION = cocotb.SIM_VERSION
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()

questa_fli = (
    SIM_NAME.startswith("modelsim")
    and LANGUAGE == "vhdl"
    and os.getenv("VHDL_GPI_INTERFACE", "") == "fli"
)

riviera_vpi_below_2024_10 = (
    SIM_NAME.startswith("riviera")
    and LANGUAGE == "verilog"
    and RivieraVersion(cocotb.SIM_VERSION) < "2024.10"
)

ghdl_before_5 = SIM_NAME.startswith("ghdl") and GhdlVersion(SIM_VERSION) < GhdlVersion(
    "5"
)

riviera_before_2022_10 = (
    SIM_NAME.startswith("riviera")
    and LANGUAGE == "vhdl"
    and RivieraVersion(SIM_VERSION) < RivieraVersion("2022.10")
)


########################################################################################
# All tests in this file MUST be run in the described order.
#
# This is because if the previous test failed, the Forced signal can still be in a
# Forced state. So the first thing each test does is Release the previously Forced
# signal in hope to not have previous tests affect the current test.
########################################################################################


async def reset(dut) -> None:
    dut.stream_in_data.value = 0
    dut.stream_out_data_comb.value = Release()
    dut.stream_out_data_registered.value = Release()
    await Timer(1, "ns")


# Force/Release doesn't work on Verilator (gh-3831)
# Release doesn't work on GHDL < 5 (gh-3830)
@cocotb.test(expect_fail=SIM_NAME.startswith("verilator") or ghdl_before_5)
async def test_hdl_writes_dont_overwrite_force_combo(dut) -> None:
    """Test Forcing then later Releasing a combo signal."""
    await reset(dut)

    # Force a driven signal.
    dut.stream_out_data_comb.value = Force(5)
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 5

    # Combo drive of the Forced signal.
    dut.stream_in_data.value = 4

    # Check Forced signal didn't change.
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 5

    # Release the Forced signal
    dut.stream_out_data_comb.value = Release()
    await Timer(1, "ns")

    # Set input signal to cause output signal to update.
    dut.stream_in_data.value = 3
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 3


# Release doesn't work on Riviera-PRO (VHPI) until version 2022.10.
# Release doesn't work on GHDL < 5 (gh-3830)
# Force/Release doesn't work on Verilator (gh-3831)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("verilator")
    or riviera_before_2022_10
    or ghdl_before_5
)
async def test_hdl_writes_dont_overwrite_force_registered(dut) -> None:
    """Test Forcing then Releasing a registered output."""
    await reset(dut)

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    # Force the driven signal.
    dut.stream_out_data_registered.value = Force(5)
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 5

    # Drive the input of the registered process.
    dut.stream_in_data.value = 4

    # Check the Forced signal didn't change
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 5

    # Release the driven signal.
    dut.stream_out_data_registered.value = Release()

    # Check that the registered drive is now propagating the input value.
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 4


# Force/Release doesn't work on Verilator (gh-3831)
@cocotb.test(expect_fail=SIM_NAME.startswith("verilator"))
async def test_multiple_force_in_same_cycle(dut) -> None:
    """Tests multiple Force in the same eval cycle write the last value."""
    await reset(dut)

    # Write several Forces
    dut.stream_out_data_comb.value = Force(67)
    dut.stream_out_data_comb.value = Force(5)
    dut.stream_out_data_comb.value = Force(9)

    # Check last value is the last write.
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 9

    # Check value is Forced.
    dut.stream_in_data.value = 1
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 9


# Force/Release doesn't work on Verilator (gh-3831)
# Release doesn't work on GHDL < 5 (gh-3830)
@cocotb.test(expect_fail=SIM_NAME.startswith("verilator") or ghdl_before_5)
async def test_multiple_release_in_same_cycle(dut) -> None:
    """Tests multiple Force in the same eval cycle write the last value."""
    await reset(dut)

    # Force a signal.
    dut.stream_out_data_comb.value = Force(31)
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 31

    # Issue multiple Releases.
    async def do_realease() -> None:
        dut.stream_out_data_comb.value = Release()

    for _ in range(10):
        cocotb.start_soon(do_realease())

    await Timer(1, "ns")

    # Check value is Released.
    dut.stream_in_data.value = 1
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 1


# Force/Release doesn't work on Verilator (gh-3831)
# Release doesn't work on GHDL < 5 (gh-3830)
# Riviera's VPI < 2024.10 stacktraces when overwriting forced signal with normal deposit (gh-3832)
# Questa's FLI allows overwriting forced signal with normal deposit (gh-3833)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("verilator") or questa_fli or ghdl_before_5,
    skip=riviera_vpi_below_2024_10,
)
async def test_deposit_on_forced(dut) -> None:
    """Test Deposits following a Force don't overwrite the value on combo signals."""
    await reset(dut)

    # Force the driven signal.
    dut.stream_out_data_comb.value = Force(10)
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 10

    # Attempt depositing on the forced signal. This shouldn't change the value.
    dut.stream_out_data_comb.value = 11
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 10

    # Release the Forced signal.
    dut.stream_out_data_comb.value = Release()

    # Check if the driven signal is actually released.
    dut.stream_out_data_comb.value = 46
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 46


# Force/Release doesn't work on Verilator (gh-3831)
# Questa's FLI allows overwriting forced signal with normal deposit (gh-3833)
# Riviera's VPI < 2024.10 stacktraces when overwriting forced signal with normal deposit (gh-3832)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("verilator") or questa_fli,
    skip=riviera_vpi_below_2024_10,
)
async def test_deposit_then_force_in_same_cycle(dut) -> None:
    """Tests a Force and Deposit in the same cycle results in Force winning."""
    await reset(dut)

    # Concurrent Force and Deposit
    dut.stream_out_data_comb.value = 2
    dut.stream_out_data_comb.value = Force(1)

    # Check Force value won
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 1

    # Check signal is Forced.
    dut.stream_in_data.value = 63
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 1


# Force/Release doesn't work on Verilator (gh-3831)
# Questa's FLI allows overwriting forced signal with normal deposit (gh-3833)
# Riviera's VPI < 2024.10 stacktraces when overwriting forced signal with normal deposit (gh-3832)
@cocotb.test(
    expect_fail=SIM_NAME.startswith("verilator") or ghdl_before_5 or questa_fli,
    skip=riviera_vpi_below_2024_10,
)
async def test_force_then_deposit_in_same_cycle(dut) -> None:
    """Tests a Force and Deposit in the same cycle results in Force winning."""
    await reset(dut)

    # Concurrent Force and Deposit
    dut.stream_out_data_comb.value = Force(1)
    dut.stream_out_data_comb.value = 2

    # Check Force value won
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 1

    # Check signal is Forced.
    dut.stream_in_data.value = 63
    await Timer(1, "ns")
    assert dut.stream_out_data_comb.value == 1


################################################################################
