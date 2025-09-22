# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def test_cocotb_runner():
    """Test main cocotb functionality using the Python runner."""
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

    # Use sample_module design
    if toplevel_lang == "verilog":
        sources = [test_dir / "designs" / "sample_module" / "sample_module.sv"]
    else:
        sources = [
            test_dir / "designs" / "sample_module" / "sample_module_package.vhdl",
            test_dir / "designs" / "sample_module" / "sample_module_1.vhdl",
            test_dir / "designs" / "sample_module" / "sample_module.vhdl",
        ]
        if sim in ["ius", "xcelium"]:
            build_args.append("-v93")

    # test_timing_triggers.py requires a 1ps time precision
    timescale = ("1ps", "1ps")

    runner.build(
        sources=sources,
        hdl_toplevel="sample_module",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
        timescale=timescale,
    )

    # The pytest_assertion_rewriting test module deliberately does not follow the
    # test_* naming convention to test that pytest assertion rewriting is enabled
    # on all test modules declared in test_module
    test_modules = [
        "test_deprecated",
        "test_synchronization_primitives",
        "test_concurrency_primitives",
        "test_tests",
        "test_testfactory",
        "test_timing_triggers",
        "test_scheduler",
        "test_clock",
        "test_edge_triggers",
        "test_async_coroutines",
        "test_async_generators",
        "test_handle",
        "test_logging",
        "pytest_assertion_rewriting",
        "test_queues",
        "test_sim_time_utils",
        "test_start_soon",
        "test_ci",
    ]

    runner.test(
        hdl_toplevel="sample_module",
        hdl_toplevel_lang=toplevel_lang,
        test_module=",".join(test_modules),
        test_args=test_args,
    )


if __name__ == "__main__":
    test_cocotb_runner()
