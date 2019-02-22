"""
Failing case for https://github.com/potentialventures/cocotb/issues/768.

Note that the bug only occurred if the test in question runs first - so
no more tests can be added to this file.
"""

import cocotb
from cocotb.triggers import Timer, ReadOnly
from cocotb.binary import BinaryValue

# this line is different between the two files
value = BinaryValue(0, n_bits=8)

@cocotb.test()
def do_test(dut):
    dut.stream_in_data.setimmediatevalue(value)
    yield Timer(1)
    assert dut.stream_in_data.value == 0
    yield ReadOnly()
