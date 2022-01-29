# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from cocotb.runner import get_runner

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
    "test_timing_triggers"
]


def test_cocotb():
    verilog_sources = []
    vhdl_sources = []
    toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")

    if toplevel_lang == "verilog":
        verilog_sources=[
            os.path.join(tests_dir, "designs", "sample_module", "sample_module.sv")
        ]
    else:
        vhdl_sources=[
            os.path.join(tests_dir, "designs", "sample_module", "sample_module_pack.vhdl"),
            os.path.join(tests_dir, "designs", "sample_module", "sample_module_1.vhdl"),
            os.path.join(tests_dir, "designs", "sample_module", "sample_module.vhdl")
        ]

    sim = os.getenv("SIM", "icarus")
    runner = get_runner(sim)()

    compile_args = ["+acc"] if sim == "questa" else []

    runner.build(
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        toplevel="sample_module",
        build_dir=sim_build,
        extra_args=compile_args)
    sim_args = ["-t", "ps"] if sim == "questa" else []

    runner.test(
        toplevel_lang=toplevel_lang,
        python_search=[os.path.join(tests_dir, "test_cases", "test_cocotb")],
        toplevel="sample_module",
        py_module=module_name,
        extra_args=sim_args)


if __name__ == "__main__":
    test_cocotb()
