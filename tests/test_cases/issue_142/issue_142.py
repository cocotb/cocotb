# A set of regression tests for open issues
from __future__ import annotations

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def issue_142_overflow_error(dut):
    """Transparently convert ints too long to pass
    through the GPI interface natively into LogicArrays"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    # Wider values are transparently converted to LogicArrays
    for value in [
        0,
        0x7F_FF_FF_FF,  # fits in a 32-bit signed int
        0x7F_FF_FF_FF_FF_FF_FF_FF,  # requires >32-bit signed int, must be transparently converted to LogicArray
    ]:
        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        assert dut.stream_in_data_wide.value == value
        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        assert dut.stream_in_data_wide.value == value
