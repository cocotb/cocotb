# A set of regression tests for open issues

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue


@cocotb.test()
def issue_142_overflow_error(dut):
    """Tranparently convert ints too long to pass
       through the GPI interface natively into BinaryValues"""
    cocotb.fork(Clock(dut.clk, 2500).start())

    def _compare(value):
        if int(dut.stream_in_data_wide.value) != int(value):
            raise TestFailure("Expecting 0x%x but got 0x%x on %s" % (
                int(value), int(dut.stream_in_data_wide.value),
                str(dut.stream_in_data_wide)))

    # Wider values are transparently converted to BinaryValues
    for value in [0, 0x7FFFFFFF, 0x7FFFFFFFFFFF, BinaryValue(0x7FFFFFFFFFFFFF,len(dut.stream_in_data_wide),bigEndian=False)]:

        dut.stream_in_data_wide <= value
        yield RisingEdge(dut.clk)
        _compare(value)
        dut.stream_in_data_wide = value
        yield RisingEdge(dut.clk)
        _compare(value)
