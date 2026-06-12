# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from pathlib import Path

from cocotb_tools.runner import get_runner

THIS_DIR = Path(__file__).resolve().parent


def build_and_run(benchmark, scenario: str) -> None:
    if str(THIS_DIR) not in sys.path:
        sys.path.append(str(THIS_DIR))

    runner = get_runner("icarus")

    runner.build(
        hdl_toplevel="task_churn_perf_top",
        sources=[THIS_DIR / "task_churn_perf_top.sv"],
        build_dir="sim_build",
    )

    @benchmark
    def run_test() -> None:
        runner.test(
            hdl_toplevel="task_churn_perf_top",
            test_module="task_churn_performance_tests",
            test_filter=scenario,
        )


def test_task_churn_typical(benchmark) -> None:
    build_and_run(benchmark, "typical")


def test_task_churn_churn_random(benchmark) -> None:
    build_and_run(benchmark, "churn_random")


def test_task_churn_resident_bulk(benchmark) -> None:
    build_and_run(benchmark, "resident_bulk")


def test_task_churn_completion_storm(benchmark) -> None:
    build_and_run(benchmark, "completion_storm")


def test_task_churn_fanout(benchmark) -> None:
    build_and_run(benchmark, "fanout")
