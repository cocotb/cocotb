"""
Control case.

This passed before the bug fix, and should continue to pass

Note that the bug only occurred if the test in question runs first - so
no more tests can be added to this file.
"""
import cocotb
from cocotb.triggers import ReadOnly, Timer

# this line is different between the two files
value = 0


@cocotb.test()
async def test(dut):
    dut.stream_in_data.setimmediatevalue(value)
    await Timer(1, "step")
    assert dut.stream_in_data.value == 0
    await ReadOnly()
