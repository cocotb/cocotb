# A set of regression tests for open issues

import cocotb
import logging


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else ())
async def issue_330_direct(dut):
    """
    Access a structure
    """

    tlog = logging.getLogger("cocotb.test")

    structure = dut.inout_if

    tlog.info(f"Value of inout_if => a_in = {structure.a_in.value} ; b_out = {structure.b_out.value}")


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME in ["Icarus Verilog"] else ())
async def issue_330_iteration(dut):
    """
    Access a structure via issue_330_iteration
    """

    tlog = logging.getLogger("cocotb.test")

    structure = dut.inout_if

    count = 0
    for member in structure:
        tlog.info("Found %s" % member._path)
        count += 1

    assert count == 2, "There should have been two members of the structure"
