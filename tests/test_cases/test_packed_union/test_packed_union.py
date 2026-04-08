# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os

import cocotb
from cocotb_tools.sim_versions import RivieraVersion

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.xfail(
    cocotb.SIM_NAME.lower().startswith("riviera")
    and RivieraVersion(cocotb.SIM_VERSION) >= RivieraVersion("2022.10")
    and RivieraVersion(cocotb.SIM_VERSION) < RivieraVersion("2024.04")
    and LANGUAGE == "verilog",
    reason="Riviera-PRO 2022.10-2023.10 (VPI) do not discover dut.t correctly (gh-3587)",
)
@cocotb.xfail(
    cocotb.SIM_NAME.lower().startswith(("verilator", "icarus")),
    raises=AttributeError,
    reason="Verilator and Icarus do not support packed unions correctly (gh-4761)",
    # Apparently some simulators allow accessing into unions as if they were structs.
)
@cocotb.test
async def test_packed_union(dut):
    pbs = dut.t
    pbs.a.value = 0
