# Copyright cocotb contributors
# Copyright (c) 2015, 2018 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer


async def reset_dut(reset_n, duration_ns):
    reset_n.value = 0
    await Timer(duration_ns)
    reset_n.value = 1
    cocotb.log.debug("Reset complete")


@cocotb.test()
async def test_dumpfile_verilator(dut):
    await reset_dut(dut.reset_n, 20)
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    await ClockCycles(dut.clk, 0xFF)

    # check that the vcd file exists and that therefore the
    # $dumfiles and $dumpargs are working
    assert Path("waves.vcd").exists()
