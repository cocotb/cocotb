# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from pathlib import Path

from cocotb_tools.runner import get_runner

THIS_DIR = Path(__file__).resolve().parent


def test_parameterize_perf_icarus(benchmark) -> None:
    if str(THIS_DIR) not in sys.path:
        sys.path.append(str(THIS_DIR))

    runner = get_runner("icarus")

    runner.build(
        hdl_toplevel="parametrize_perf_top",
        sources=[THIS_DIR / "parametrize_perf_top.sv"],
        build_dir="sim_build",
    )

    @benchmark
    def run_test() -> None:
        runner.test(
            hdl_toplevel="parametrize_perf_top",
            test_module="parametrize_performance_tests",
            test_filter="parametrize/a=49/b=49/c=49",
        )
