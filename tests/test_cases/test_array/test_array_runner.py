# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner


@pytest.mark.skipif(
    os.getenv("SIM", "icarus").lower() in ["icarus", "verilator"],
    reason="This simulator doesn't support structs",
)
def test_array_runner():
    """Test array using the Python runner."""
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

    # Use array_module design
    if toplevel_lang == "verilog":
        sources = [test_dir / "designs" / "array_module" / "array_module.sv"]
    else:
        sources = [
            test_dir / "designs" / "array_module" / "array_module_pack.vhd",
            test_dir / "designs" / "array_module" / "array_module.vhd",
        ]
        if sim in ["ius", "xcelium"]:
            build_args.append("-v93")

    runner.build(
        sources=sources,
        hdl_toplevel="array_module",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    runner.test(
        hdl_toplevel="array_module",
        hdl_toplevel_lang=toplevel_lang,
        test_module="test_array",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_array_runner()
