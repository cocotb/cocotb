"""
Failing case.

Note that the bug only occurred if the test in question runs first - so
no more tests can be added to this file.
"""

import cocotb
from cocotb.triggers import ReadOnly, Timer
from cocotb.types import LogicArray, Range

# this line is different between the two files
value = LogicArray.from_unsigned(0, Range(7, "downto", 0))


@cocotb.test()
async def do_test(dut):
    dut.stream_in_data.setimmediatevalue(value)
    await Timer(1, "step")
    assert dut.stream_in_data.value == 0
    await ReadOnly()
