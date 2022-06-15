# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os

import pytest

import cocotb
from cocotb.triggers import Timer

is_questa_vhpi = (
    cocotb.SIM_NAME.lower().startswith("modelsim")
    and os.environ["VHDL_GPI_INTERFACE"] == "vhpi"
)


@cocotb.test()
async def test_long_signal(dut):
    """Write and read a normal signal (longer than 0)."""
    dut.data_in.value = 0x5
    await Timer(1, "ns")
    assert dut.data_out == 0x5, "Failed to readback dut.data_out"


@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith(
        ("ghdl", "xmsim", "ncsim", "riviera", "aldec")
    )
    or is_questa_vhpi
    else ()
)
async def test_read_zero_signal(dut):
    """Read a zero vector. It should always read 0."""
    assert dut.Cntrl_out == 0, "Failed to readback dut.Cntrl_out"


@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith(
        ("ghdl", "xmsim", "ncsim", "riviera", "aldec")
    )
    or is_questa_vhpi
    else ()
)
async def test_write_zero_signal_with_0(dut):
    """Write a zero vector with 0."""
    dut.Cntrl_out.value = 0x0
    await Timer(1, "ns")
    assert dut.Cntrl_out == 0, "Failed to readback dut.Cntrl_out"


@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith(
        ("ghdl", "xmsim", "ncsim", "riviera", "aldec")
    )
    or is_questa_vhpi
    else ()
)
async def test_write_zero_signal_with_1(dut):
    """Write a zero vector with 1. Should catch a "out of range" exception."""
    with pytest.raises(OverflowError):
        dut.Cntrl_out.value = 0x1
