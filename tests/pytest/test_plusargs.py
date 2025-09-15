# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner

pytestmark = pytest.mark.simulator_required

src_path = Path(__file__).resolve().parent.parent / "designs" / "plusargs_module"

test_module_path = (
    Path(__file__).resolve().parent.parent / "test_cases" / "test_plusargs"
)

sys.path.insert(0, str(test_module_path))


def test_toplevel_library():
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    vhdl_gpi_interfaces = os.getenv("VHDL_GPI_INTERFACE", None)
    sim = os.getenv("SIM", "icarus" if hdl_toplevel_lang == "verilog" else "nvc")

    runner = get_runner(sim)

    build_test_args = []
    if hdl_toplevel_lang == "vhdl" and sim == "xcelium":
        build_test_args = ["-v93"]
    if sim == "verilator":
        build_test_args = ["--timing"]

    if hdl_toplevel_lang == "verilog":
        sources = [src_path / "tb_top.v"]
        gpi_interfaces = ["vpi"]
    else:
        sources = [src_path / "tb_top.vhd"]
        gpi_interfaces = [vhdl_gpi_interfaces]

    runner.build(
        sources=sources,
        hdl_toplevel="tb_top",
        build_dir=str(test_module_path / "sim_build" / "pytest"),
        build_args=build_test_args,
    )

    runner.test(
        hdl_toplevel="tb_top",
        test_module="plusargs",
        test_args=build_test_args,
        gpi_interfaces=gpi_interfaces,
        plusargs=["+foo=bar", "+test1", "+test2", "+options=fubar", "+lol=wow=4"],
    )
