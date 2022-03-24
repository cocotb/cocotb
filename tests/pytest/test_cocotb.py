# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os

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
    "test_pytest",
    "test_queues",
    "test_scheduler",
    "test_synchronization_primitives",
    "test_testfactory",
    "test_tests",
    "test_timing_triggers",
]

verilog_sources = []
vhdl_sources = []
toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")

if toplevel_lang == "verilog":
    verilog_sources = [
        os.path.join(tests_dir, "designs", "sample_module", "sample_module.sv")
    ]
else:
    vhdl_sources = [
        os.path.join(tests_dir, "designs", "sample_module", "sample_module_pack.vhdl"),
        os.path.join(tests_dir, "designs", "sample_module", "sample_module_1.vhdl"),
        os.path.join(tests_dir, "designs", "sample_module", "sample_module.vhdl"),
    ]

sim = os.getenv("SIM", "icarus")
compile_args = []
sim_args = []
if sim == "questa":
    compile_args = ["+acc"]
    sim_args = ["-t", "ps"]
elif sim == "xcelium":
    compile_args = ["-v93"]

toplevel = "sample_module"
python_search = [os.path.join(tests_dir, "test_cases", "test_cocotb")]


def test_cocotb():

    runner = get_runner(sim)()

    runner.build(
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        toplevel=toplevel,
        build_dir=sim_build,
        extra_args=compile_args,
    )

    runner.test(
        toplevel_lang=toplevel_lang,
        python_search=python_search,
        toplevel=toplevel,
        py_module=module_name,
        extra_args=sim_args,
    )


if __name__ == "__main__":
    test_cocotb()
