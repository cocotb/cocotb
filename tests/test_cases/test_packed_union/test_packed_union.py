# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import cocotb
from cocotb._sim_versions import RivieraVersion


# Riviera-PRO 2022.10-2023.10 (VPI) do not discover dut.t correctly (gh-3587)
@cocotb.test(
    expect_error=Exception
    if cocotb.SIM_NAME.lower().startswith(("verilator", "icarus", "ghdl"))
    or (
        cocotb.SIM_NAME.lower().startswith("riviera")
        and RivieraVersion(cocotb.SIM_VERSION) >= RivieraVersion("2022.10")
        and RivieraVersion(cocotb.SIM_VERSION) < RivieraVersion("2024.04")
        and cocotb.LANGUAGE == "verilog"
    )
    else ()
)
async def test_packed_union(dut):
    dut.t.a.value = 0
