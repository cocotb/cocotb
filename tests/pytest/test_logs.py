# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from test_cocotb import (
    compile_args,
    gpi_interfaces,
    hdl_toplevel,
    hdl_toplevel_lang,
    sim_args,
    sim_build,
    tests_dir,
    verilog_sources,
    vhdl_sources,
)

import cocotb
from cocotb.clock import Clock
from cocotb.runner import get_runner
from cocotb.triggers import ClockCycles

sys.path.insert(0, str(Path(tests_dir) / "pytest"))
test_module = Path(__file__).stem
sim = os.getenv("SIM", "icarus")


@cocotb.test()
async def clock_design(dut):
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 10)


def run_simulation(sim, log_dir):
    runner = get_runner(sim)
    runner.build(
        always=True,
        clean=True,
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        hdl_toplevel=hdl_toplevel,
        build_dir=sim_build,
        build_args=compile_args,
        defines={"NODUMPFILE": 1},
        log_file=log_dir / "build.log",
    )

    runner.test(
        hdl_toplevel_lang=hdl_toplevel_lang,
        hdl_toplevel=hdl_toplevel,
        gpi_interfaces=gpi_interfaces,
        test_module=test_module,
        test_args=sim_args,
        build_dir=sim_build,
        log_file=log_dir / "test.log",
    )


@pytest.mark.simulator_required
def test_wave_dump():
    temp_dir = TemporaryDirectory()
    log_dir = Path(temp_dir.name)
    run_simulation(sim=sim, log_dir=log_dir)
    assert (log_dir / "build.log").exists()
    assert (log_dir / "test.log").exists()
