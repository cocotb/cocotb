# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import cocotb


@cocotb.test(
    expect_error=Exception
    if cocotb.SIM_NAME.lower().startswith(("verilator", "icarus", "ghdl"))
    else ()
)
async def test_packed_union(dut):
    dut.t.a.value = 0
