# A set of regression tests for open issues

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue


@cocotb.test(expect_error=True)
def false_double(dut):
    yield Timer(0)

    dut.aclk = float(1.0)

    yield Timer(1)

