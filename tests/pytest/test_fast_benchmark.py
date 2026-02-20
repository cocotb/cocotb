# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Simulator-based benchmark: compare cocotb.fast vs standard cocotb.

Runs a tight read/write loop using both the standard cocotb API and the
fast API, then reports the speedup.  Requires a Verilog simulator.

Run manually::

    SIM=icarus pytest tests/pytest/test_fast_benchmark.py -v -s

Or via the CI workflow which handles simulator setup.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner

# Mark every test in this module as requiring a simulator
pytestmark = pytest.mark.simulator_required

# The benchmark HDL is in profile_bench/
BENCH_DIR = Path(__file__).resolve().parent.parent.parent / "profile_bench"


@pytest.fixture(scope="module")
def sim_build(tmp_path_factory):
    """Build the benchmark HDL once per module."""
    sim = os.getenv("SIM", "icarus")
    build_dir = tmp_path_factory.mktemp("sim_build")

    runner = get_runner(sim)
    runner.build(
        sources=[BENCH_DIR / "bench_module.sv"],
        hdl_toplevel="bench_module",
        always=True,
        build_dir=build_dir,
    )
    return runner, build_dir


def test_fast_api_builds(sim_build):
    """Verify the fast API benchmark tests can be loaded by the simulator."""
    sys.path.insert(0, str(BENCH_DIR))
    try:
        bench = importlib.import_module("bench_signals")
        assert hasattr(bench, "bench_signal_rw")
        assert hasattr(bench, "bench_fast_loop")
        assert hasattr(bench, "bench_fast_sched")
    finally:
        sys.path.pop(0)


def test_fast_signal_rw(sim_build):
    """Run the standard signal rw benchmark and the fast-loop version back-to-back."""
    runner, build_dir = sim_build

    # Run standard and fast benchmarks — the test itself reports metrics via cocotb.log
    # This test verifies both versions run without error against the same HDL
    runner.test(
        hdl_toplevel="bench_module",
        test_module="bench_signals",
        testcase="bench_signal_rw,bench_fast_loop",
        test_dir=str(BENCH_DIR),
        build_dir=build_dir,
    )


def test_fast_sched(sim_build):
    """Run the fast mini-scheduler benchmark."""
    runner, build_dir = sim_build

    runner.test(
        hdl_toplevel="bench_module",
        test_module="bench_signals",
        testcase="bench_fast_sched",
        test_dir=str(BENCH_DIR),
        build_dir=build_dir,
    )
