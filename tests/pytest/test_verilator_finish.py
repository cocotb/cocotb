# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner

pytestmark = [
    pytest.mark.simulator_required,
    pytest.mark.skipif(os.getenv("SIM") != "verilator", reason="Verilator only"),
]

tests_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(tests_dir / "test_cases" / "test_verilator_finish"))


def test_no_eval_after_finish(tmp_path):
    runner = get_runner("verilator")
    runner.build(
        sources=[tests_dir / "designs" / "verilator_finish" / "top.sv"],
        hdl_toplevel="top",
        build_dir=tmp_path,
        timescale=("1ns", "1ps"),
    )
    runner.test(
        hdl_toplevel="top",
        test_module="write_then_finish",
        build_dir=tmp_path,
        timescale=("1ns", "1ps"),
    )
