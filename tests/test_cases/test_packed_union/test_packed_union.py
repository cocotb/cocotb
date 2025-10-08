# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os

import cocotb
from cocotb_tools.sim_versions import RivieraVersion

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


# Riviera-PRO 2022.10-2023.10 (VPI) do not discover dut.t correctly (gh-3587)
@cocotb.test(
    expect_error=Exception
    if cocotb.SIM_NAME.lower().startswith(("verilator", "icarus", "ghdl"))
    or (
        cocotb.SIM_NAME.lower().startswith("riviera")
        and RivieraVersion(cocotb.SIM_VERSION) >= RivieraVersion("2022.10")
        and RivieraVersion(cocotb.SIM_VERSION) < RivieraVersion("2024.04")
        and LANGUAGE == "verilog"
    )
    else (AttributeError)
)
async def test_packed_union(dut):
    pbs = dut.t
    pbs.a.value = 0
