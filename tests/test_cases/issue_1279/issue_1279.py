"""
Test that once a SimFailure occurs, no further tests are run
"""
import cocotb


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith("riviera"),  # gh-1859
    expect_error=cocotb.result.SimFailure,
    stage=1,
)
def test_sim_failure_a(dut):
    # invoke a deadlock, as nothing is driving this clock
    yield cocotb.triggers.RisingEdge(dut.clk)


@cocotb.test(
    skip=cocotb.SIM_NAME.lower().startswith("riviera"),  # gh-1859
    expect_error=cocotb.result.SimFailure,
    stage=2,
)
def test_sim_failure_b(dut):
    yield cocotb.triggers.NullTrigger()
    raise cocotb.result.TestFailure("This test should never run")
