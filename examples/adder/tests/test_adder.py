# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
# Simple tests for an adder module
from __future__ import annotations

import os
import random
import sys
from pathlib import Path

import cocotb
from cocotb.triggers import Timer
from cocotb_tools.runner import get_runner

if cocotb.simulator.is_running():
    from adder_model import adder_model


@cocotb.test()
async def adder_basic_test(dut):
    """Test for 5 + 10"""

    A = 5
    B = 10

    dut.A.value = A
    dut.B.value = B

    await Timer(2, unit="ns")

    assert dut.X.value == adder_model(A, B), (
        f"Adder result is incorrect: {dut.X.value} != 15"
    )


@cocotb.test()
async def adder_randomised_test(dut):
    """Test for adding 2 random numbers multiple times"""

    for _ in range(10):
        A = random.randint(0, 15)
        B = random.randint(0, 15)

        dut.A.value = A
        dut.B.value = B

        await Timer(2, unit="ns")

        assert dut.X.value == adder_model(A, B), (
            f"Randomised test failed with: {dut.A.value} + {dut.B.value} = {dut.X.value}"
        )


def test_adder_runner():
    """Simulate the adder example using the Python runner.

    This file can be run directly or via pytest discovery.
    """
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent
    # equivalent to setting the PYTHONPATH environment variable
    sys.path.append(str(proj_path / "model"))

    if hdl_toplevel_lang == "verilog":
        sources = [proj_path / "hdl" / "adder.sv"]
    else:
        sources = [proj_path / "hdl" / "adder.vhdl"]

    build_test_args = []
    if hdl_toplevel_lang == "vhdl" and sim == "xcelium":
        build_test_args = ["-v93"]

    # equivalent to setting the PYTHONPATH environment variable
    sys.path.append(str(proj_path / "tests"))

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="adder",
        always=True,
        build_args=build_test_args,
    )
    runner.test(
        hdl_toplevel="adder", test_module="test_adder", test_args=build_test_args
    )


if __name__ == "__main__":
    test_adder_runner()
