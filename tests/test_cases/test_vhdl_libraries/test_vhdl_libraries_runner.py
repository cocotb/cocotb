# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner


@pytest.mark.skipif(
    os.getenv("TOPLEVEL_LANG", "verilog").lower() != "vhdl",
    reason="This test only supports VHDL",
)
@pytest.mark.skipif(
    os.getenv("SIM", "ghdl").lower()
    not in [
        "ghdl",
        "nvc",
        "questa",
        "questa-compat",
        "questa-qisqrun",
        "modelsim",
        "xcelium",
        "ius",
        "riviera",
    ],
    reason="Only GHDL, NVC, Questa/ModelSim, Xcelium, Incisive and Riviera-PRO are supported",
)
def test_vhdl_libraries_runner():
    """Test VHDL libraries using the Python runner."""
    sim = os.getenv("SIM", "ghdl")
    toplevel_lang = "vhdl"  # This test is VHDL-only

    runner = get_runner(sim)

    proj_path = Path(__file__).resolve().parent

    # Build arguments based on simulator
    build_args = []
    test_args = []

    if sim == "questa":
        build_args = ["+acc"]
        test_args = ["-t", "ps"]
    elif sim == "xcelium":
        build_args = ["-v93"]

    # VHDL sources with library specification
    sources = [proj_path / "a.vhdl"]

    # Additional VHDL sources for blib library
    [proj_path / "b.vhdl"]

    # Build with library support
    runner.build(
        sources=sources,
        hdl_toplevel="a",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
        # Note: VHDL library handling may need to be implemented differently
        # depending on the specific runner implementation
    )

    runner.test(
        hdl_toplevel="a",
        hdl_toplevel_lang=toplevel_lang,
        test_module="test_ab",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_vhdl_libraries_runner()
