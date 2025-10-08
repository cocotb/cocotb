# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


# GHDL is unable to access signals in generate loops (gh-2594)
# Verilator doesn't support vpiGenScope or vpiGenScopeArray (gh-1884)
# VCS is unable to access signals in generate loops
@cocotb.test(
    expect_error=AssertionError
    if cocotb.SIM_NAME.lower().startswith("ghdl")
    else AttributeError
    if cocotb.SIM_NAME.lower().startswith("verilator")
    else AttributeError
    if "vcs" in cocotb.SIM_NAME.lower()
    else ()
)
async def test_distinct_generates(dut):
    assert len(dut.foobar) == 10
    assert len(dut.foo) == 6
