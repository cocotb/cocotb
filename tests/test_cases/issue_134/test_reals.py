import logging
import random
import sys

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue


@cocotb.test(expect_error=cocotb.SIM_NAME in ["Icarus Verilog"])
def assign_double(dut):
    """
    Assign a random floating point value, read it back from the DUT and check
    it matches what we assigned
    """
    val = random.uniform(-1e307, 1e307)
    log = logging.getLogger("cocotb.test")
    yield Timer(1)
    log.info("Setting the value %g" % val)
    dut.stream_in_real = val
    yield Timer(1)
    yield Timer(1) # Workaround for VHPI scheduling - needs investigation
    got = float(dut.stream_out_real)
    log.info("Read back value %g" % got)
    if got != val:
        raise TestFailure("Values didn't match!")
