# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner

pytestmark = pytest.mark.simulator_required

src_path = (
    Path(__file__).resolve().parent.parent
    / "test_cases"
    / "test_vhdl_libraries_multiple"
)
sys.path.insert(0, str(src_path))


@pytest.mark.skipif(
    os.getenv("HDL_TOPLEVEL_LANG", "vhdl") != "vhdl",
    reason="Skipping test since only VHDL is supported",
)
@pytest.mark.skipif(
    os.getenv("SIM", "ghdl") not in ["ghdl", "nvc", "questa", "riviera"],
    reason="Skipping test since only GHDL, NVC, Questa/ModelSim, and Riviera are supported",
)
def test_toplevel_library():
    vhdl_gpi_interfaces = os.getenv("VHDL_GPI_INTERFACE", None)
    gpi_interfaces = [vhdl_gpi_interfaces]

    sim = os.getenv("SIM", "ghdl")
    runner = get_runner(sim)

    compile_args = []
    if sim == "xcelium":
        compile_args = ["-v93"]

    # Build additional libraries
    for lib in ["e", "d", "c", "b"]:
        runner.build(
            hdl_library=f"{lib}lib",
            sources=[src_path / f"{lib}.vhdl"],
            build_args=compile_args,
            build_dir=str(src_path / "sim_build" / "pytest"),
        )

    # Build main hdl_library
    lib = "a"
    runner.build(
        hdl_library=f"{lib}lib",
        sources=[src_path / f"{lib}.vhdl"],
        hdl_toplevel="a",
        build_args=compile_args,
        build_dir=str(src_path / "sim_build" / "pytest"),
    )

    runner.test(
        hdl_toplevel="a",
        hdl_toplevel_library="alib",
        test_module="test_abcde",
        gpi_interfaces=gpi_interfaces,
    )
