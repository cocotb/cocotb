# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner

THIS_DIR = Path(__file__).resolve().parent


@pytest.mark.parametrize("size", [16, 1024])
@pytest.mark.parametrize("descending", [False, True])
@pytest.mark.parametrize("offset", [0, 7])
@pytest.mark.parametrize("input_kind", ["list", "array"])
@pytest.mark.parametrize("write_phase", ["first", "repeated"])
def test_unpacked_array_write(
    benchmark, tmp_path, size, descending, offset, input_kind, write_phase
):
    if str(THIS_DIR) not in sys.path:
        sys.path.append(str(THIS_DIR))
    left, right = offset, offset + size - 1
    if descending:
        left, right = right, left
    runner = get_runner("icarus")
    runner.build(
        hdl_toplevel="unpacked_array_perf",
        sources=[THIS_DIR / "unpacked_array_perf.sv"],
        parameters={"LEFT": left, "RIGHT": right},
        build_dir=tmp_path / "sim_build",
        timescale=("1ns", "1ps"),
    )
    measurements_file = tmp_path / "measurements.json"
    samples = []

    def run_test():
        measurements_file.unlink(missing_ok=True)
        runner.test(
            hdl_toplevel="unpacked_array_perf",
            test_module="unpacked_array_performance_tests",
            extra_env={
                "MEMORY_LEFT": str(left),
                "MEMORY_RIGHT": str(right),
                "INPUT_KIND": input_kind,
                "WRITE_PHASE": write_phase,
                "MEASUREMENTS_FILE": str(measurements_file),
            },
            test_dir=tmp_path,
        )
        samples.append(json.loads(measurements_file.read_text(encoding="utf-8")))

    benchmark.pedantic(run_test, rounds=3, iterations=1, warmup_rounds=0)
    benchmark.extra_info["assignment_samples"] = samples
