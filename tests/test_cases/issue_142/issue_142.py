# A set of regression tests for open issues

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(
    expect_error=cocotb.triggers.TriggerException
    if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"]
    else ()
)
async def issue_142_overflow_error(dut):
    """Tranparently convert ints too long to pass
    through the GPI interface natively into BinaryValues"""
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    def _compare(value):
        assert int(dut.stream_in_data_wide.value) == int(
            value
        ), "Expecting 0x{:x} but got 0x{:x} on {}".format(
            int(value), int(dut.stream_in_data_wide.value), str(dut.stream_in_data_wide)
        )

    # Wider values are transparently converted to BinaryValues
    for value in [
        0,
        0x7FFFFFFF,
        0x7FFFFFFFFFFF,
        BinaryValue(0x7FFFFFFFFFFFFF, len(dut.stream_in_data_wide), bigEndian=False),
    ]:

        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        _compare(value)
        dut.stream_in_data_wide.value = value
        await RisingEdge(dut.clk)
        _compare(value)
