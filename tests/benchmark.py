# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import sys
from pathlib import Path

from cocotb.runner import get_runner


def build_and_run_matrix_multiplier(benchmark, sim):

    hdl_toplevel_lang = "verilog"
    extra_args = []

    if sim == "ghdl":
        extra_args = ["--std=08"]
        hdl_toplevel_lang = "vhdl"

    verilog_sources = []
    vhdl_sources = []

    proj_path = (
        Path(__file__).resolve().parent.parent / "examples" / "matrix_multiplier"
    )

    sys.path.append(str(proj_path / "tests"))

    if hdl_toplevel_lang == "verilog":
        verilog_sources = [proj_path / "hdl" / "matrix_multiplier.sv"]
    else:
        vhdl_sources = [
            proj_path / "hdl" / "matrix_multiplier_pkg.vhd",
            proj_path / "hdl" / "matrix_multiplier.vhd",
        ]

    runner = get_runner(sim)

    runner.build(
        hdl_toplevel="matrix_multiplier",
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        build_args=extra_args,
    )

    @benchmark
    def run_test():
        runner.test(
            hdl_toplevel="matrix_multiplier",
            hdl_toplevel_lang=hdl_toplevel_lang,
            test_module="test_matrix_multiplier",
            test_args=extra_args,
        )


def test_matrix_multiplier_icarus(benchmark):
    build_and_run_matrix_multiplier(benchmark, "icarus")


def test_matrix_multiplier_ghdl(benchmark):
    build_and_run_matrix_multiplier(benchmark, "ghdl")
