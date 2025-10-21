# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner

LANG = os.getenv("TOPLEVEL_LANG", "verilog")


@pytest.mark.skipif(LANG != "verilog", reason="This test only supports Verilog")
def test_log_prefix() -> None:
    sim = os.getenv("SIM", "icarus")
    runner = get_runner(sim)

    pwd = Path(__file__).parent.absolute()

    # select args
    build_args = []
    test_args = []
    if sim == "questa":
        build_args = ["+acc"]
        test_args = ["-t", "ps"]
    elif sim == "xcelium":
        build_args = ["-v93"]

    runner.build(
        sources=[pwd / "top.sv"],
        hdl_toplevel="top",
        build_args=build_args,
    )

    runner.test(
        test_module="log_prefix_tests",
        hdl_toplevel="top",
        hdl_toplevel_lang=LANG,
        test_args=test_args,
        test_filter="test_log_prefix_custom",
        extra_env={
            "COCOTB_LOG_PREFIX": "{ANSI.YELLOW_FG}abc{ANSI.DEFAULT_FG} {record.levelname} {record.created_sim_time} {record.name[:4]:>10} ",
            "COCOTB_ANSI_OUTPUT": "1",
        },
    )

    runner.test(
        test_module="log_prefix_tests",
        hdl_toplevel="top",
        hdl_toplevel_lang=LANG,
        test_args=test_args,
        test_filter="test_log_prefix_default",
    )

    runner.test(
        test_module="log_prefix_tests",
        hdl_toplevel="top",
        hdl_toplevel_lang=LANG,
        test_args=test_args,
        test_filter="test_log_prefix_default",
        extra_env={"COCOTB_REDUCED_LOG_FMT": "0"},
    )
