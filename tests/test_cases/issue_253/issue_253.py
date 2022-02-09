# A set of regression tests for open issues

import cocotb
from cocotb.triggers import Timer


async def toggle_clock(dut):
    dut.clk.value = 0
    await Timer(10, "ns")
    assert dut.clk.value.integer == 0, "Clock not set to 0 as expected"
    dut.clk.value = 1
    await Timer(10, "ns")
    assert dut.clk.value.integer == 1, "Clock not set to 1 as expected"


@cocotb.test()
async def issue_253_empty(dut):
    await toggle_clock(dut)


@cocotb.test()
async def issue_253_none(dut):
    await toggle_clock(dut)


@cocotb.test()
async def issue_253_notset(dut):
    await toggle_clock(dut)
