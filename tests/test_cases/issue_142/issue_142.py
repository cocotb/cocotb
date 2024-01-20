# A set of regression tests for open issues

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.types import LogicArray, Range


@cocotb.test()
async def issue_142_overflow_error(dut):
    """Tranparently convert ints too long to pass
    through the GPI interface natively into LogicArrays"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    # Wider values are transparently converted to LogicArrays
    for value in [
        0,
        0x7FFFFFFF,
        0x7FFFFFFFFFFF,
        LogicArray(
            0x7FFFFFFFFFFFFF, Range(len(dut.stream_in_data_wide) - 1, "downto", 0)
        ),
    ]:
        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        assert dut.stream_in_data_wide.value.integer == value
        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        assert dut.stream_in_data_wide.value.integer == value
