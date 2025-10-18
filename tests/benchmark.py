# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from pathlib import Path

from cocotb_tools.runner import get_runner


def build_and_run_matrix_multiplier(benchmark, sim):
    hdl_toplevel_lang = "verilog"
    build_args = []
    test_args = []

    if sim == "nvc":
        build_args = ["--std=08"]
        hdl_toplevel_lang = "vhdl"

    proj_path = (
        Path(__file__).resolve().parent.parent / "examples" / "matrix_multiplier"
    )

    sys.path.append(str(proj_path / "tests"))

    if hdl_toplevel_lang == "verilog":
        sources = [proj_path / "hdl" / "matrix_multiplier.sv"]
    else:
        sources = [
            proj_path / "hdl" / "matrix_multiplier_pkg.vhd",
            proj_path / "hdl" / "matrix_multiplier.vhd",
        ]

    runner = get_runner(sim)

    runner.build(
        hdl_toplevel="matrix_multiplier",
        sources=sources,
        build_args=build_args,
    )

    @benchmark
    def run_test():
        runner.test(
            hdl_toplevel="matrix_multiplier",
            hdl_toplevel_lang=hdl_toplevel_lang,
            test_module="matrix_multiplier_tests",
            test_args=test_args,
            seed=123456789,
        )


def test_matrix_multiplier_icarus(benchmark):
    build_and_run_matrix_multiplier(benchmark, "icarus")


def test_matrix_multiplier_nvc(benchmark):
    build_and_run_matrix_multiplier(benchmark, "nvc")
