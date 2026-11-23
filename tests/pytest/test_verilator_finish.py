# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys

import pytest

from cocotb_tools.runner import get_runner

pytestmark = [
    pytest.mark.simulator_required,
    pytest.mark.skipif(os.getenv("SIM") != "verilator", reason="Verilator only"),
]

design = """
module top(input logic x);
  logic a, b;
  always @(x) a = x;
  always @(a) b = a;
  final if (b) $error("design was evaluated after vpi_finish");
endmodule
"""

test_module = """
import cocotb
from cocotb.triggers import ReadWrite, Timer

@cocotb.test()
async def write_then_finish(dut):
    await Timer(1, "ns")
    await ReadWrite()
    dut.x.value = 1
"""


def test_no_eval_after_finish(tmp_path):
    (tmp_path / "top.sv").write_text(design)
    (tmp_path / "write_then_finish.py").write_text(test_module)
    sys.path.insert(0, str(tmp_path))

    runner = get_runner("verilator")
    runner.build(
        sources=[tmp_path / "top.sv"],
        hdl_toplevel="top",
        build_dir=tmp_path / "sim_build",
        timescale=("1ns", "1ps"),
    )
    runner.test(
        hdl_toplevel="top",
        test_module="write_then_finish",
        build_dir=tmp_path / "sim_build",
        timescale=("1ns", "1ps"),
    )
