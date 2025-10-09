# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner


@pytest.mark.skipif(
    os.getenv("TOPLEVEL_LANG", "verilog") != "verilog",
    reason="This test only supports Verilog",
)
def test_test_sv_interface_runner():
    """Test test_sv_interface using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")

    runner = get_runner(sim)

    Path(__file__).resolve().parent

    # Build arguments based on simulator
    build_args = []
    test_args = []

    if sim == "questa":
        build_args = ["+acc"]
        test_args = ["-t", "ps"]
    elif sim == "xcelium":
        build_args = ["-v93"]

    # Sources based on original Makefile
    if toplevel_lang == "verilog":
        sources = [
            Path("$(shell"),
            Path("pwd)/top.sv"),
        ]
    else:
        sources = []  # No VHDL sources found

    # Additional build args for VHDL with certain simulators
    if toplevel_lang == "vhdl" and sim in ["ius", "xcelium"]:
        if "-v93" not in build_args:
            build_args.append("-v93")

    runner.build(
        sources=sources,
        hdl_toplevel="top",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    runner.test(
        hdl_toplevel="top",
        hdl_toplevel_lang=toplevel_lang,
        test_module="test_sv_if",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_test_sv_interface_runner()
