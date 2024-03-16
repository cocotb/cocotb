# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os

import cocotb
from cocotb._sim_versions import RivieraVersion

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


# Riviera-PRO 2022.10 (VPI) and newer does not discover dut.t correctly (gh-3587)
@cocotb.test(
    expect_error=Exception
    if cocotb.SIM_NAME.lower().startswith(("verilator", "icarus", "ghdl"))
    or (
        cocotb.SIM_NAME.lower().startswith("riviera")
        and RivieraVersion(cocotb.SIM_VERSION) >= RivieraVersion("2022.10")
        and LANGUAGE == "verilog"
    )
    else ()
)
async def test_packed_union(dut):
    dut.t.a.value = 0
