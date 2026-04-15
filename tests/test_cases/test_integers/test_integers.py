# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from pathlib import Path

import pytest

from cocotb_tools.runner import get_runner
from cocotb_tools.sim_versions import IcarusVersion

SIM = os.getenv("SIM", "icarus").lower()


@pytest.mark.skipif(
    SIM == "icarus" and IcarusVersion.from_commandline() < IcarusVersion("12.0"),
    reason="Icarus v11.0 treats integers as regs and ports cannot be of type reg",
)
def test_integers_runner():
    hdl_toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog").lower()

    proj_path = Path(__file__).resolve().parent

    if hdl_toplevel_lang == "verilog":
        sources = [proj_path / "integers.sv"]
    else:
        sources = [
            proj_path / "integers_pkg.vhdl",
            proj_path / "integers.vhdl",
        ]

    build_args = []
    if hdl_toplevel_lang == "vhdl" and SIM in ("ius", "xcelium"):
        build_args = ["-v93"]

    runner = get_runner(SIM)
    runner.build(
        sources=sources,
        hdl_toplevel="top",
        build_args=build_args,
    )
    runner.test(
        hdl_toplevel="top",
        test_module="integer_tests",
        test_args=build_args,
    )


if __name__ == "__main__":
    test_integers_runner()
