"""
This file is public domain, it can be freely copied without restrictions."
SPDX-License-Identifier: CC0-1.0
"""

# test_runner.py

import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def test_simple_counter():
    """
    Creates sources list, gets a cocotb Python Runner,
    Builds HDL, runs cocotb testcases.
    """
    proj_path = Path(__file__).resolve().parent

    sources = [proj_path / "simple_counter.sv"]

    sim = os.getenv("SIM", "icarus")
    runner = get_runner(sim)

    runner.build(
        sources=sources,
        hdl_toplevel="simple_counter",
        waves=True,
    )

    runner.test(
        hdl_toplevel="simple_counter",
        test_module="simple_counter_testcases,",
        waves=True,
    )


if __name__ == "__main__":
    test_simple_counter()
