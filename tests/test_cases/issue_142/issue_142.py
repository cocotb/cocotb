# A set of regression tests for open issues

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


@cocotb.test()
async def issue_142_overflow_error(dut):
    """Tranparently convert ints too long to pass
    through the GPI interface natively into BinaryValues"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    # Wider values are transparently converted to BinaryValues
    for value in [
        0,
        0x7FFFFFFF,
        0x7FFFFFFFFFFF,
        BinaryValue(0x7FFFFFFFFFFFFF, len(dut.stream_in_data_wide), bigEndian=False),
    ]:
        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        assert dut.stream_in_data_wide.value.integer == value
        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        assert dut.stream_in_data_wide.value.integer == value
