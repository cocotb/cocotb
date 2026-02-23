"""
Test that once a simulation failure occurs, no further tests are run
"""

from __future__ import annotations

import cocotb
from cocotb.regression import SimFailure
from cocotb.triggers import RisingEdge


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith("riviera"),  # gh-1859
    expect_error=SimFailure,
)
async def test_sim_failure_a(dut):
    # invoke a deadlock, as nothing is driving this clock
    await RisingEdge(dut.clk)


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith("riviera"),  # gh-1859
    expect_error=SimFailure,
)
async def test_sim_failure_b(dut):
    assert False, "This test should never run"
