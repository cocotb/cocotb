# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
from __future__ import annotations

import os
from pathlib import Path

from cocotb_tools.runner import get_runner

LANGUAGE = os.getenv("TOPLEVEL_LANG", "verilog").lower().strip()


def test_tri_state_bus_runner():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    if LANGUAGE == "verilog":
        sources = [proj_path / "bus_master.sv"]
    else:
        sources = [proj_path / "bus_master.vhdl"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="bus_master",
        always=True,
    )

    runner.test(hdl_toplevel="bus_master", test_module="tri_state_bus_tests")


if __name__ == "__main__":
    test_tri_state_bus_runner()
