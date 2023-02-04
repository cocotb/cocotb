# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
from pathlib import Path

import pytest

from cocotb.runner import get_runner

pytestmark = pytest.mark.simulator_required

src_path = Path(__file__).resolve().parent.parent / "designs" / "plusargs_module"

test_module_path = (
    Path(__file__).resolve().parent.parent / "test_cases" / "test_plusargs"
)

sys.path.insert(0, str(test_module_path))


def test_toplevel_library():

    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    vhdl_gpi_interfaces = os.getenv("VHDL_GPI_INTERFACE", None)
    sim = os.getenv("SIM", "icarus")

    runner = get_runner(sim)

    test_args = []
    if sim == "xcelium":
        test_args = ["-v93"]

    verilog_sources = []
    vhdl_sources = []

    if hdl_toplevel_lang == "verilog":
        verilog_sources = [src_path / "tb_top.v"]
        gpi_interfaces = ["vpi"]
    else:
        vhdl_sources = [src_path / "tb_top.vhd"]
        gpi_interfaces = [vhdl_gpi_interfaces]

    runner.build(
        vhdl_sources=vhdl_sources,
        verilog_sources=verilog_sources,
        hdl_toplevel="tb_top",
        build_dir=str(test_module_path / "sim_build" / "pytest"),
    )

    runner.test(
        hdl_toplevel="tb_top",
        test_module="plusargs",
        test_args=test_args,
        gpi_interfaces=gpi_interfaces,
        plusargs=["+foo=bar", "+test1", "+test2", "+options=fubar", "+lol=wow=4"],
    )
