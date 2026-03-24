"""Runner script for the profiling benchmark."""

from __future__ import annotations

import os
from pathlib import Path

from cocotb_tools.runner import get_runner

proj_path = Path(__file__).resolve().parent


def run():
    sim = os.getenv("SIM", "verilator")
    runner = get_runner(sim)
    runner.build(
        sources=[proj_path / "bench_module.sv"],
        hdl_toplevel="bench_module",
        always=True,
        build_dir=proj_path / "sim_build",
    )
    runner.test(
        hdl_toplevel="bench_module",
        test_module="bench_signals",
        test_dir=str(proj_path),
    )


if __name__ == "__main__":
    run()
