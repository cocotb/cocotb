# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def test_test_3316_a_runner():
    """Test test_3316_a using the Python runner."""
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
        sources = [Path("../test_3316/test_3316.sv")]
    else:
        sources = []  # No VHDL sources found

    # Additional build args for VHDL with certain simulators
    if toplevel_lang == "vhdl" and sim in ["ius", "xcelium"]:
        if "-v93" not in build_args:
            build_args.append("-v93")

    runner.build(
        sources=sources,
        hdl_toplevel="test_3316",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    runner.test(
        hdl_toplevel="test_3316",
        hdl_toplevel_lang=toplevel_lang,
        test_module="test_3316_a",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_test_3316_a_runner()
