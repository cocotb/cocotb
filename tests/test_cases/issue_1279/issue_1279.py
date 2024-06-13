"""
Test that once a simulation failure occurs, no further tests are run
"""

import cocotb


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith("riviera"),  # gh-1859
    _expect_sim_failure=True,
)
async def test_sim_failure_a(dut):
    # invoke a deadlock, as nothing is driving this clock
    await cocotb.triggers.RisingEdge(dut.clk)


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith("riviera"),  # gh-1859
    _expect_sim_failure=True,
)
async def test_sim_failure_b(dut):
    assert False, "This test should never run"
