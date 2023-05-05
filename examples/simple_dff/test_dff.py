# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.runner import get_runner
from cocotb.triggers import RisingEdge
from cocotb.types import LogicArray


@cocotb.test()
async def dff_simple_test(dut):
    """Test that d propagates to q"""

    # Set initial input value to prevent it from floating
    dut.d.setimmediatevalue(1)
    # Assert initial output is unknown
    assert LogicArray(dut.q.value) == LogicArray('X')

    clock = Clock(dut.clk, 10, units="us")  # Create a 10us period clock on port clk
    cocotb.start_soon(clock.start(start_high=False))  # Start the clock

    await RisingEdge(dut.clk) # Synchronize with the clock
    expected_val = 1 # Matches initial input value
    for i in range(10):
        val = random.randint(0, 1)
        dut.d.value = val  # Assign the random value val to the input port d
        await RisingEdge(dut.clk)
        assert dut.q.value == expected_val, f"output q was incorrect on the {i}th cycle"
        expected_val = val

    # Check the final input on the next clock
    await RisingEdge(dut.clk)  # Synchronize with the clock
    assert dut.q.value == expected_val, f"output q was incorrect on the last cycle"


def test_simple_dff_runner():

    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    verilog_sources = []
    vhdl_sources = []

    if hdl_toplevel_lang == "verilog":
        verilog_sources = [proj_path / "dff.sv"]
    else:
        vhdl_sources = [proj_path / "dff.vhdl"]

    runner = get_runner(sim)
    runner.build(
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        hdl_toplevel="dff",
        always=True,
    )

    runner.test(hdl_toplevel="dff", test_module="test_dff,")


if __name__ == "__main__":
    test_simple_dff_runner()
