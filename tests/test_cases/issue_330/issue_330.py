# A set of regression tests for open issues

import logging
import os

import cocotb
from cocotb._sim_versions import RivieraVersion

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


# GHDL unable to access record signals (gh-2591)
# Icarus doesn't support structs (gh-2592)
# Verilator doesn't support structs (gh-1275)
# Riviera-PRO 2022.10 and newer does not discover inout_if correctly over VPI (gh-3587)
@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith(("icarus", "ghdl", "verilator"))
    or (
        SIM_NAME.startswith("riviera")
        and RivieraVersion(cocotb.SIM_VERSION) >= RivieraVersion("2022.10")
        and LANGUAGE == "verilog"
    )
    else ()
)
async def issue_330_direct(dut):
    """
    Access a structure
    """

    tlog = logging.getLogger("cocotb.test")

    structure = dut.inout_if

    tlog.info(
        f"Value of inout_if => a_in = {structure.a_in.value} ; b_out = {structure.b_out.value}"
    )


# GHDL unable to access record signals (gh-2591)
# Icarus doesn't support structs (gh-2592)
# Verilator doesn't support structs (gh-1275)
@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith(("icarus", "ghdl"))
    else AssertionError
    if SIM_NAME.startswith("verilator")
    else ()
)
async def issue_330_iteration(dut):
    """
    Access a structure via issue_330_iteration
    """

    tlog = logging.getLogger("cocotb.test")

    structure = dut.inout_if

    count = 0
    for member in structure:
        tlog.info(f"Found {member._path}")
        count += 1

    # Riviera-PRO 2022.10 and newer does not discover inout_if correctly over VPI (gh-3587)
    rv_2022_10_plus = RivieraVersion(cocotb.SIM_VERSION) >= RivieraVersion("2022.10")
    if SIM_NAME.startswith("riviera") and rv_2022_10_plus and LANGUAGE == "verilog":
        assert count == 0
    else:
        assert count == 2, "There should have been two members of the structure"
