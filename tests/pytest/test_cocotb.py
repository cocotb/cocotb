# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys

import pytest

from cocotb.runner import get_runner

pytestmark = pytest.mark.simulator_required

tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sim_build = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_build")

module_name = [
    "test_async_coroutines",
    "test_async_generators",
    "test_clock",
    "test_concurrency_primitives",
    "test_deprecated",
    "test_edge_triggers",
    "test_generator_coroutines",
    "test_handle",
    "test_logging",
    "pytest_assertion_rewriting",
    "test_queues",
    "test_scheduler",
    "test_synchronization_primitives",
    "test_testfactory",
    "test_tests",
    "test_timing_triggers",
]

verilog_sources = []
vhdl_sources = []
hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
vhdl_gpi_interfaces = os.getenv("VHDL_GPI_INTERFACE", None)

if hdl_toplevel_lang == "verilog":
    verilog_sources = [
        os.path.join(tests_dir, "designs", "sample_module", "sample_module.sv")
    ]
    gpi_interfaces = ["vpi"]
else:
    vhdl_sources = [
        os.path.join(tests_dir, "designs", "sample_module", "sample_module_pack.vhdl"),
        os.path.join(tests_dir, "designs", "sample_module", "sample_module_1.vhdl"),
        os.path.join(tests_dir, "designs", "sample_module", "sample_module.vhdl"),
    ]
    gpi_interfaces = [vhdl_gpi_interfaces]

sim = os.getenv("SIM", "icarus")
compile_args = []
sim_args = []
if sim == "questa":
    compile_args = ["+acc"]
    sim_args = ["-t", "ps"]
elif sim == "xcelium":
    compile_args = ["-v93"]

hdl_toplevel = "sample_module"
sys.path.insert(0, os.path.join(tests_dir, "test_cases", "test_cocotb"))


def test_cocotb():

    runner = get_runner(sim)

    runner.build(
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        hdl_toplevel=hdl_toplevel,
        build_dir=sim_build,
        build_args=compile_args,
    )

    runner.test(
        hdl_toplevel_lang=hdl_toplevel_lang,
        hdl_toplevel=hdl_toplevel,
        test_module=module_name,
        gpi_interfaces=gpi_interfaces,
        test_args=sim_args,
    )


if __name__ == "__main__":
    test_cocotb()
