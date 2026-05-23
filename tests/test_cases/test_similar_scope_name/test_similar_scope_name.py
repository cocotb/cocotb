# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Test for issue #2255: a scope whose name starts another scope is returned instead."""

from __future__ import annotations

import cocotb


@cocotb.xfail(
    cocotb.SIM_NAME.lower().startswith("ghdl"),
    raises=AssertionError,
    reason="GHDL is unable to access signals in generate loops (gh-2594)",
)
@cocotb.xfail(
    cocotb.SIM_NAME.lower().startswith("verilator"),
    raises=AttributeError,
    reason="Verilator doesn't support vpiGenScope or vpiGenScopeArray (gh-1884)",
)
@cocotb.xfail(
    "vcs" in cocotb.SIM_NAME.lower(),
    raises=AttributeError,
    reason="VCS is unable to access signals in generate loops",
)
@cocotb.test
async def test_distinct_generates(dut):
    assert len(dut.foobar) == 10
    assert len(dut.foo) == 6
