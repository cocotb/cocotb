# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ReadOnly, RisingEdge
from cocotb_tools.runner import get_runner


@cocotb.test
async def dff_simple_test(dut):
    """Test that d propagates to q"""

    # Set initial input value to prevent it from floating
    dut.d.value = 0

    clock = Clock(dut.clk, 10, units="us")  # Create a 10us period clock on port clk
    # Start the clock. Start it low to avoid issues on the first RisingEdge
    cocotb.start_soon(clock.start(start_high=False))

    # generate stimulus
    stimulus = [random.randint(0, 1) for _ in range(10)]

    # calculated expected outputs
    expecteds = [val for val in stimulus]

    async def drive_input():
        for val in stimulus:
            await RisingEdge(dut.clk)  # Synchronize with clock before driving.
            dut.d.value = val  # Assign the stimulus value to the input port 'd'.

    # Run the driver coroutine concurrently to the monitoring and checking logic below.
    cocotb.start_soon(drive_input())

    # Wait 1 clock cycle for input to propagate to output.
    await RisingEdge(dut.clk)

    for expected_val in expecteds:
        await RisingEdge(dut.clk)  # Synchronize with clock, then...
        await ReadOnly()  # Wait for all signal changes to settle.
        assert (
            dut.q.value == expected_val
        )  # Check the actual output against the expected.


def test_simple_dff_runner():
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    if hdl_toplevel_lang == "verilog":
        sources = [proj_path / "dff.sv"]
    else:
        sources = [proj_path / "dff.vhdl"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="dff",
        always=True,
    )

    runner.test(hdl_toplevel="dff", test_module="test_dff,")


if __name__ == "__main__":
    test_simple_dff_runner()
