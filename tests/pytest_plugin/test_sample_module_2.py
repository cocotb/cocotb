# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test HDL DUT ``sample_module``."""

from __future__ import annotations

from cocotb.triggers import FallingEdge


async def test_dut(dut) -> None:
    """Test used to test DUT from other test module."""
    dut.stream_in_data.value = 2
    await FallingEdge(dut.clk)
    assert dut.stream_out_data_registered.value == 2
