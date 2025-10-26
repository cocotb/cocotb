# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Testing sample module."""

from __future__ import annotations

from cocotb.clock import Clock
from cocotb.triggers import FallingEdge


async def test_pass(dut) -> None:
    pass


async def test_simple(dut) -> None:
    """Test sample module with simple data transfer."""
    dut.clk.value = 0
    dut.stream_in_valid.value = 0
    dut.stream_in_data.value = 0
    dut.stream_out_ready.value = 0

    Clock(dut.clk, 10, unit="ns").start(start_high=False)

    dut.stream_in_valid.value = 1
    dut.stream_out_ready.value = 1
    await FallingEdge(dut.clk)

    dut.stream_in_data.value = 10
    await FallingEdge(dut.clk)

    assert dut.stream_out_data_registered.value == 10
