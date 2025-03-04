# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

# test_runner.py

import os
from pathlib import Path

from cocotb_tools.runner import get_runner


def test_sync_register_access_runner():
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent

    sources = [proj_path / "register.sv"]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="register",
    )

    runner.test(hdl_toplevel="register", test_module="test_sync_register_access,")


if __name__ == "__main__":
    test_sync_register_access_runner()
