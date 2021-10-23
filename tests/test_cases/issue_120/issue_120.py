# A set of regression tests for open issues

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly


async def send_data(dut):
    dut.stream_in_valid.value = 1
    await RisingEdge(dut.clk)
    dut.stream_in_valid.value = 0


async def monitor(dut):
    for i in range(4):
        await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.stream_in_valid.value.integer, "stream_in_valid should be high on the 5th cycle"


# Cadence simulators: "Unable set up RisingEdge(...) Trigger" with VHDL (see #1076)
@cocotb.test(expect_error=cocotb.triggers.TriggerException if cocotb.SIM_NAME.startswith(("xmsim", "ncsim")) and cocotb.LANGUAGE in ["vhdl"] else ())
async def issue_120_scheduling(dut):

    cocotb.start_soon(Clock(dut.clk, 10, 'ns').start())
    cocotb.start_soon(monitor(dut))
    await RisingEdge(dut.clk)

    # First attempt, not from coroutine - works as expected
    for i in range(2):
        dut.stream_in_valid.value = 1
        await RisingEdge(dut.clk)
        dut.stream_in_valid.value = 0

    await RisingEdge(dut.clk)

    # Failure - we don't drive valid on the rising edge even though
    # behaviour should be identical to the above
    await send_data(dut)
    dut.stream_in_valid.value = 1
    await RisingEdge(dut.clk)
    dut.stream_in_valid.value = 0

    await RisingEdge(dut.clk)
