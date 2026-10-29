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

    runner = get_runner("verilator")

    runner.build(
        hdl_toplevel="packed_array_perf",
        sources=[THIS_DIR / "packed_array_perf.sv"],
        build_dir="sim_build/test_packed_array",
    )

    @benchmark
    def run_test() -> None:
        runner.test(
            hdl_toplevel="packed_array_perf",
            test_module="packed_array_performance_tests",
            test_filter=f"{scenario}$",
        )


def test_packed_array_write_flat_2d(benchmark) -> None:
    build_and_run(benchmark, "write_flat_2d")


def test_packed_array_read_flat_2d(benchmark) -> None:
    build_and_run(benchmark, "read_flat_2d")


def test_packed_array_write_indexed_2d(benchmark) -> None:
    build_and_run(benchmark, "write_indexed_2d")


def test_packed_array_write_read_indexed_3d(benchmark) -> None:
    build_and_run(benchmark, "write_read_indexed_3d")


def test_packed_array_value_change_element_2d(benchmark) -> None:
    build_and_run(benchmark, "value_change_element_2d")


def test_packed_array_value_change_3d(benchmark) -> None:
    build_and_run(benchmark, "value_change_3d")


def test_packed_array_value_change_bit_3d(benchmark) -> None:
    build_and_run(benchmark, "value_change_bit_3d")


def test_packed_array_value_change_middle_3d(benchmark) -> None:
    build_and_run(benchmark, "value_change_middle_3d")


def test_packed_array_edge_storm_2d(benchmark) -> None:
    build_and_run(benchmark, "edge_storm_2d")


def test_packed_array_edge_storm_3d(benchmark) -> None:
    build_and_run(benchmark, "edge_storm_3d")
