# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Tests the Force/Freeze/Release features."""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, Timer

SIM_NAME = cocotb.SIM_NAME.lower()


# Release doesn't work on GHDL (gh-3830)
# Force/Release doesn't work on Verilator (gh-3831)
@cocotb.test(expect_fail=SIM_NAME.startswith(("ghdl", "verilator")))
async def test_hdl_writes_dont_overwrite_force_combo(dut):
    """Test Forcing then later Releasing a combo signal."""

    dut.stream_in_data.value = 4

    # Force the driven signal.
    dut.stream_out_data_comb.value = Force(5)
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 5

    # Release the driven signal.
    # The driver signal is set again to trigger the process which recomputes the driven signal.
    # This is done because releasing the driven signal does not cause the process to run again.
    dut.stream_in_data.value = 3
    dut.stream_out_data_comb.value = Release()
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 3


# Release doesn't work on GHDL (gh-3830)
# Force/Release doesn't work on Verilator (gh-3831)
@cocotb.test(expect_fail=SIM_NAME.startswith(("ghdl", "verilator")))
async def test_hdl_writes_dont_overwrite_force_registered(dut):
    """Test Forcing then Releasing a registered output."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 4

    # Force the driven signal.
    dut.stream_out_data_registered.value = Force(5)
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 5

    # Release the driven signal.
    dut.stream_out_data_registered.value = Release()
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 4


# Release doesn't work on GHDL (gh-3830)
# Force/Release doesn't work on Verilator (gh-3831)
@cocotb.test(expect_fail=SIM_NAME.startswith("ghdl"))
async def test_force_followed_by_release_combo(dut):
    """Test if Force followed immediately by Release works on combo signals."""

    dut.stream_in_data.value = 14

    # Force driven signal then immediately release it.
    dut.stream_out_data_comb.value = Force(23)
    dut.stream_out_data_comb.value = Release()

    # Check if the driven signal is actually released.
    # The driver signal is set again to trigger the process which recomputes the driven signal.
    # This is done because releasing the driven signal does not cause the process to run again.
    dut.stream_in_data.value = 16
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 16


# Release doesn't work on GHDL (gh-3830)
# Force/Release doesn't work on Verilator (gh-3831)
@cocotb.test(expect_fail=SIM_NAME.startswith("ghdl"))
async def test_force_followed_by_release_registered(dut):
    """Test if Force followed immediately by Release works on registered signals."""

    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 90

    # Force driven signal then immediately release it.
    dut.stream_out_data_registered.value = Force(5)
    dut.stream_out_data_registered.value = Release()

    # Check if the driven signal is actually released.
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 90


questa_fli = (
    SIM_NAME.startswith("modelsim") and os.getenv("VHDL_GPI_INTERFACE", "") == "fli"
)


riviera_vpi = (
    SIM_NAME.startswith("riviera")
    and os.getenv("TOPLEVEL_LANG", "verilog") == "verilog"
)


# Release doesn't work on GHDL (gh-3830)
# Force/Release doesn't work on Verilator (gh-3831)
# Riviera's VPI implicitly releases signal when overwriting forced signal with normal deposit (gh-3832)
# Questa's FLI allows overwriting forced signal with normal deposit (gh-3833)
@cocotb.test(
    expect_fail=SIM_NAME.startswith(("ghdl", "verilator")) or riviera_vpi or questa_fli
)
async def test_cocotb_writes_dont_overwrite_force_combo(dut):
    """Test Deposits following a Force don't overwrite the value on combo signals."""
    dut.stream_in_data.value = 56

    # Force the driven signal.
    dut.stream_out_data_comb.value = Force(10)
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 10

    # Attempt depositing on the forced signal. This shouldn't change the value.
    dut.stream_out_data_comb.value = 11
    dut.stream_in_data.value = 70  # attempt to trigger a change in value
    await Timer(10, "ns")
    assert dut.stream_out_data_comb.value == 10

    # Release the forced signal. The value should follow driver.
    # The driver signal is set again to trigger the process which recomputes the driven signal.
    # This is done because releasing the driven signal does not cause the process to run again.
    dut.stream_in_data.value = 46
    dut.stream_out_data_registered.value = Release()
    await Timer(10, "ns")
    assert dut.stream_in_data.value == 46


# Release doesn't work on GHDL (gh-3830)
# Force/Release doesn't work on Verilator (gh-3831)
# Riviera's VPI implicitly releases signal when overwriting forced signal with normal deposit (gh-3832)
# Questa's FLI allows overwriting forced signal with normal deposit (gh-3833)
@cocotb.test(
    expect_fail=SIM_NAME.startswith(("ghdl", "verilator")) or questa_fli or riviera_vpi
)
async def test_cocotb_writes_dont_overwrite_force_registered(dut):
    """Test Deposits following a Force don't overwrite the value on registered signals."""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 77

    # Force the driven signal.
    dut.stream_out_data_registered.value = Force(10)
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 10

    # Attempt depositing on the forced signal. This shouldn't change the value.
    dut.stream_out_data_registered.value = 11
    await ClockCycles(dut.clk, 2)
    assert dut.stream_out_data_registered.value == 10

    # Release the forced signal. The value should follow driver.
    dut.stream_out_data_registered.value = Release()
    await ClockCycles(dut.clk, 2)
    assert dut.stream_in_data.value == 77


# Release and Freeze read current simulator values, not scheduled values (gh-3829)
@cocotb.test(expect_fail=True)
async def test_force_followed_by_release_correct_value(dut):
    """Test if Forcing then immediately Releasing a signal yields the correct value.

    Due to the way that Release and Freeze are implemented (reading the current value then doing a set with that value) this test will always fail.
    Leaving this test for when a better implementation of Freeze and Release are implemented.
    """
    dut.stream_in_data.value = 19
    await Timer(10, "ns")
    assert dut.stream_in_data.value == 19

    dut.stream_in_data.value = Force(0)
    dut.stream_in_data.value = Release()
    await Timer(10, "ns")
    assert dut.stream_in_data.value == 0
