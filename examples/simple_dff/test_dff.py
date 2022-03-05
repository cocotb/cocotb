# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.runner import get_runner
from cocotb.triggers import FallingEdge


@cocotb.test()
async def dff_simple_test(dut):
    """Test that d propagates to q"""

    clock = Clock(dut.clk, 10, units="us")  # Create a 10us period clock on port clk
    cocotb.start_soon(clock.start())  # Start the clock

    await FallingEdge(dut.clk)  # Synchronize with the clock
    for i in range(10):
        val = random.randint(0, 1)
        dut.d.value = val  # Assign the random value val to the input port d
        await FallingEdge(dut.clk)
        assert dut.q.value == val, f"output q was incorrect on the {i}th cycle"


def test_simple_dff_runner():

    toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    verilog_sources = []
    vhdl_sources = []

    if toplevel_lang == "verilog":
        verilog_sources = [proj_path / "dff.sv"]
    else:
        vhdl_sources = [proj_path / "dff.vhdl"]

    runner = get_runner(sim)()
    runner.build(
        verilog_sources=verilog_sources, vhdl_sources=vhdl_sources, toplevel="dff"
    )

    runner.test(toplevel="dff", py_module="test_dff")


if __name__ == "__main__":
    test_simple_dff_runner()
