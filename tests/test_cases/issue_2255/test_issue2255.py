# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import logging

import cocotb


# GHDL is unable to access signals in generate loops (gh-2594)
# Verilator doesn't support vpiGenScope or vpiGenScopeArray (gh-1884)
@cocotb.test(
    expect_error=AssertionError
    if cocotb.SIM_NAME.lower().startswith("ghdl")
    else AttributeError
    if cocotb.SIM_NAME.lower().startswith("verilator")
    else ()
)
async def test_distinct_generates(dut):
    tlog = logging.getLogger("cocotb.test")

    foobar = dut.foobar
    foo = dut.foo

    tlog.info("Length of foobar is %d", len(foobar))
    tlog.info("Length of foo is %d", len(foo))

    assert len(foobar) == 10
    assert len(foo) == 6
