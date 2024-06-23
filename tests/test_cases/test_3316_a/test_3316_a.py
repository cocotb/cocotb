# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def clk_in_coroutine(dut):
    dut.d.value = 0
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start(start_high=False))
    await RisingEdge(dut.clk)
    for _ in range(3):
        val = random.randint(0, 1)
        dut.d.value = val
        await RisingEdge(dut.clk)


@cocotb.test()
async def clk_in_hdl(dut):
    dut.d.value = 0
    await RisingEdge(dut.clk)
    for _ in range(3):
        val = random.randint(0, 1)
        dut.d.value = val
        await RisingEdge(dut.clk)
