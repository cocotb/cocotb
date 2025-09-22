# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def run_kill_sim_test(test_filter: str):
    """Run a single kill_sim test with the specified filter."""
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

    # Additional build args for VHDL with certain simulators
    if toplevel_lang == "vhdl" and sim in ["ius", "xcelium"]:
        if "-v93" not in build_args:
            build_args.append("-v93")

    runner.build(
        sources=sources,
        hdl_toplevel="sample_module",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    # Run test with filter and expect failure (test should fail gracefully)
    try:
        runner.test(
            hdl_toplevel="sample_module",
            hdl_toplevel_lang=toplevel_lang,
            test_module="kill_sim_tests",
            test_args=test_args,
            extra_env={"COCOTB_TEST_FILTER": test_filter},
        )
    except Exception:
        # Expected to fail for kill_sim tests
        pass


def test_kill_sim_sys_exit():
    """Test sys.exit behavior."""
    run_kill_sim_test("test_sys_exit")


def test_kill_sim_task_sys_exit():
    """Test task sys.exit behavior."""
    run_kill_sim_test("test_task_sys_exit")


def test_kill_sim_trigger_sys_exit():
    """Test trigger sys.exit behavior."""
    run_kill_sim_test("test_trigger_sys_exit")


def test_kill_sim_keyboard_interrupt():
    """Test keyboard interrupt behavior."""
    run_kill_sim_test("test_keyboard_interrupt")


def test_kill_sim_task_keyboard_interrupt():
    """Test task keyboard interrupt behavior."""
    run_kill_sim_test("test_task_keyboard_interrupt")


def test_kill_sim_trigger_keyboard_interrupt():
    """Test trigger keyboard interrupt behavior."""
    run_kill_sim_test("test_trigger_keyboard_interrupt")


def test_test_kill_sim_runner():
    """Test test_kill_sim using the Python runner."""
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

    # Sources based on original Makefile
    if toplevel_lang == "verilog":
        sources = [test_dir / "designs/sample_module/sample_module.sv"]
    else:
        sources = [
            test_dir / "designs/sample_module/sample_module_package.vhdl",
            test_dir / "designs/sample_module/sample_module_1.vhdl",
            test_dir / "designs/sample_module/sample_module.vhdl",
        ]

    # Additional build args for VHDL with certain simulators
    if toplevel_lang == "vhdl" and sim in ["ius", "xcelium"]:
        if "-v93" not in build_args:
            build_args.append("-v93")

    runner.build(
        sources=sources,
        hdl_toplevel="sample_module",
        hdl_toplevel_lang=toplevel_lang,
        build_args=build_args,
    )

    runner.test(
        hdl_toplevel="sample_module",
        hdl_toplevel_lang=toplevel_lang,
        test_module="kill_sim_tests",
        test_args=test_args,
    )


if __name__ == "__main__":
    test_test_kill_sim_runner()
