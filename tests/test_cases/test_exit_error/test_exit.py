# A set of regression tests for open issues

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue

# This will cause the sim to exit but we want to do this nicely
# If this was in another module then the remaining tests would also fail

@cocotb.test(expect_error=True)
def typosyntax_error():
    yield Timer(100)a
