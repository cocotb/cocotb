# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Test force, freeze and release on simulation handles"""
import logging

import cocotb
from cocotb.triggers import Timer
from cocotb.handle import Force, Release, Freeze


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower() in ["ghdl"])
async def test_force_release(dut):
    """Test force and release."""
    log = logging.getLogger("cocotb.test")
    dut.stream_in_data = 4
    dut.stream_out_data_comb = Force(5)
    await Timer(10, "ns")
    got_in = dut.stream_in_data.value
    got_out = dut.stream_out_data_comb.value
    log.info("dut.stream_in_data = %d", got_in)
    log.info("dut.stream_out_data_comb = %d", got_out)
    assert (
        got_in != got_out
    ), "stream_in_data and stream_out_data_comb should not match when force is active!"

    dut.stream_out_data_comb = Release()
    dut.stream_in_data = 3
    await Timer(10, "ns")
    got_in = dut.stream_in_data.value
    got_out = dut.stream_out_data_comb.value
    log.info("dut.stream_in_data = %d", got_in)
    log.info("dut.stream_out_data_comb = %d", got_out)
    assert (
        got_in == got_out
    ), "stream_in_data and stream_out_data_comb should match when output was released!"


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower() in ["ghdl"])
async def test_freeze(dut):
    """Test freeze."""
    log = logging.getLogger("cocotb.test")
    dut.stream_in_data = 7
    await Timer(10, "ns")
    dut.stream_in_data = Freeze()
    dut.stream_out_data_comb = Force(8)
    await Timer(10, "ns")
    got_in = dut.stream_in_data.value
    got_out = dut.stream_out_data_comb.value
    log.info("dut.stream_in_data = %d", got_in)
    log.info("dut.stream_out_data_comb = %d", got_out)
    assert (
        got_in != got_out
    ), "stream_in_data and stream_out_data_comb should not match when freeze is active!"

    dut.stream_in_data = Release()
    dut.stream_out_data_comb = Release()
    await Timer(10, "ns")
    dut.stream_in_data = 6
    await Timer(10, "ns")
    got_in = dut.stream_in_data.value
    got_out = dut.stream_out_data_comb.value
    log.info("dut.stream_in_data = %d", got_in)
    log.info("dut.stream_out_data_comb = %d", got_out)
    assert (
        got_in == got_out
    ), "stream_in_data and stream_out_data_comb should match when output was released!"


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith(("icarus")),
    expect_fail=cocotb.SIM_NAME.lower() in ["ghdl"],
)
async def test_force_release_struct(dut):
    """Test force and release on structs."""
    log = logging.getLogger("cocotb.test")
    dut.inout_if.a_in = Force(1)
    await Timer(10, "ns")
    assert dut.inout_if.a_in.value == 1
    assert (
        dut.inout_if.b_out.value == 1,
        "forced value should be visible at the other side of the assign",
    )
    dut.inout_if.a_in = Release()


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith(("icarus")),
    expect_fail=cocotb.SIM_NAME.lower() in ["ghdl"],
)
async def test_freeze_struct(dut):
    """Test freeze on structs."""
    log = logging.getLogger("cocotb.test")
    dut.inout_if.a_in = 1
    await Timer(10, "ns")
    dut.inout_if.a_in = Freeze()
    await Timer(10, "ns")
    dut.inout_if.a_in = 0  # should have no effect
    await Timer(10, "ns")
    assert dut.inout_if.a_in.value == 1
    assert (
        dut.inout_if.b_out.value == 1
    ), "frozen value should be visible at the other side of the assign"
    dut.inout_if.a_in = Release()
