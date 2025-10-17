# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def test_test_plusargs_runner():
    """Test test_plusargs using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")

    runner = get_runner(sim)

    proj_path = Path(__file__).resolve().parent
    test_dir = proj_path.parent.parent

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
        sources = [test_dir / "designs/plusargs_module/tb_top.v"]
    else:
        sources = [test_dir / "designs/plusargs_module/tb_top.vhd"]

    # Additional build args for VHDL with certain simulators
    if toplevel_lang == "vhdl" and sim in ["ius", "xcelium"]:
        if "-v93" not in build_args:
            build_args.append("-v93")

    runner.build(
        sources=sources,
        hdl_toplevel="tb_top",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    # Add plusargs to test args
    plusargs = ["+foo=bar", "+test1", "+test2", "+options=fubar", "+lol=wow=4"]
    test_args.extend(plusargs)

    runner.test(
        hdl_toplevel="tb_top",
        hdl_toplevel_lang=toplevel_lang,
        test_module="plusargs",
        test_args=test_args,
        extra_env={"COCOTB_PLUSARGS": " ".join(plusargs)},
    )


if __name__ == "__main__":
    test_test_plusargs_runner()
