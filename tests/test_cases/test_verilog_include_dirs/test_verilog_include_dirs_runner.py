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
def test_verilog_include_dirs_runner():
    """Test Verilog include directories using the Python runner."""
    sim = os.getenv("SIM", "icarus")
    toplevel_lang = "verilog"  # This test is Verilog-only

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

    # Verilog sources with include directories
    sources = [proj_path / "simple_and.sv"]

    # Include directories
    include_dirs = [proj_path / "common", proj_path / "const_stream"]

    # Add include directories to build args
    for inc_dir in include_dirs:
        if sim in ["icarus"]:
            build_args.append(f"-I{inc_dir}")
        elif sim in ["questa", "modelsim"]:
            build_args.append(f"+incdir+{inc_dir}")
        elif sim in ["xcelium", "ius"]:
            build_args.append("-incdir")
            build_args.append(str(inc_dir))
        elif sim in ["verilator"]:
            build_args.append(f"-I{inc_dir}")

    runner.build(
        sources=sources,
        hdl_toplevel="simple_and",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    runner.test(
        hdl_toplevel="simple_and",
        hdl_toplevel_lang=toplevel_lang,
        test_module="test_verilog_include_dirs",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_verilog_include_dirs_runner()
