# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys

import pytest

from cocotb_tools.runner import get_runner

pytestmark = pytest.mark.simulator_required

tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sim_build = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_build")

module_name = [
    "test_async_coroutines",
    "test_async_generators",
    "test_clock",
    "test_first_combine",
    "test_deprecated",
    "test_edge_triggers",
    "test_handle",
    "test_logging",
    "pytest_assertion_rewriting",
    "test_queues",
    "test_scheduler",
    "test_synchronization_primitives",
    "test_testfactory",
    "test_tests",
    "test_timing_triggers",
    "test_sim_time_utils",
]

hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
vhdl_gpi_interfaces = os.getenv("VHDL_GPI_INTERFACE", None)

if hdl_toplevel_lang == "verilog":
    sources = [os.path.join(tests_dir, "designs", "sample_module", "sample_module.sv")]
    gpi_interfaces = ["vpi"]
    sim = os.getenv("SIM", "icarus")
else:
    sources = [
        os.path.join(
            tests_dir, "designs", "sample_module", "sample_module_package.vhdl"
        ),
        os.path.join(tests_dir, "designs", "sample_module", "sample_module_1.vhdl"),
        os.path.join(tests_dir, "designs", "sample_module", "sample_module.vhdl"),
    ]
    gpi_interfaces = [vhdl_gpi_interfaces]
    sim = os.getenv("SIM", "nvc")
compile_args = []
sim_args = []
if sim == "questa":
    compile_args = ["+acc"]
    sim_args = ["-t", "ps"]
elif sim == "xcelium":
    compile_args = ["-v93"]
elif sim == "nvc":
    compile_args = ["--std=08"]

hdl_toplevel = "sample_module"
sys.path.insert(0, os.path.join(tests_dir, "test_cases", "test_cocotb"))

# test_timing_triggers.py requires a 1ps time precision.
timescale = ("1ps", "1ps")


def test_cocotb():
    runner = get_runner(sim)

    runner.build(
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        build_dir=sim_build,
        build_args=compile_args,
        timescale=timescale,
    )

    runner.test(
        hdl_toplevel_lang=hdl_toplevel_lang,
        hdl_toplevel=hdl_toplevel,
        test_module=module_name,
        gpi_interfaces=gpi_interfaces,
        test_args=sim_args,
        timescale=None if sim in ("xcelium",) else timescale,
    )


if __name__ == "__main__":
    test_cocotb()
