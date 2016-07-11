# A set of regression tests for open issues

import cocotb
import logging
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue

@cocotb.test(skip=cocotb.SIM_NAME in ["Icarus Verilog"])
def issue_330_direct(dut):
    """
    Access a structure
    """

    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)

    structure = dut.inout_if

    tlog.info("Value of inout_if => a_in = %s ; b_out = %s" % (structure.a_in, structure.b_out))

@cocotb.test(skip=cocotb.SIM_NAME in ["Icarus Verilog"])
def issue_330_iteration(dut):
    """
    Access a structure via issue_330_iteration
    """

    tlog = logging.getLogger("cocotb.test")
    yield Timer(10)

    structure = dut.inout_if

    count = 0
    for member in structure:
        tlog.info("Found %s" % member)
        count += 1

    if count != 2:
        raise TestFailure("There should have been two members of the structure")

