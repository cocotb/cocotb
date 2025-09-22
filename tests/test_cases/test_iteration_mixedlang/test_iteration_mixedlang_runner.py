# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def test_test_iteration_mixedlang_runner():
    """Test test_iteration_mixedlang using the Python runner."""
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

    # Use sample_module design as default
    if toplevel_lang == "verilog":
        sources = [test_dir / "designs" / "sample_module" / "sample_module.sv"]
    else:
        sources = [
            test_dir / "designs" / "sample_module" / "sample_module_package.vhdl",
            test_dir / "designs" / "sample_module" / "sample_module_1.vhdl",
            test_dir / "designs" / "sample_module" / "sample_module.vhdl",
        ]

    # Additional build args for VHDL with certain simulators
    if toplevel_lang == "vhdl" and sim in ["ius", "xcelium"]:
        if "-v93" not in build_args:
            build_args.append("-v93")

    runner.build(
        sources=sources,
        hdl_toplevel="verilog_toplevel",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    runner.test(
        hdl_toplevel="verilog_toplevel",
        hdl_toplevel_lang=toplevel_lang,
        test_module="test_iteration",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_test_iteration_mixedlang_runner()
