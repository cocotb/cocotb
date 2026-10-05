# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""https://github.com/cocotb/cocotb/issues/5094"""
from __future__ import annotations

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge


@cocotb.test
async def issue_5094_icarus_segmentation_fault(dut):
    """Write to input without awaitable at the end of the test."""
    Clock(dut.clk, 10, unit="ns").start(start_high=False)

    dut.stream_in_data.value = 0
    await FallingEdge(dut.clk)
    dut.stream_in_data.value = 0

    # Icarus will crash with segmentation fault when simulation exits
    # Workaround: at the end of the test add an additional awaitable
    # await FallingEdge(dut.clk)
