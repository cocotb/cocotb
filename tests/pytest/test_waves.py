import os
import sys

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

sys.path.insert(0, os.path.join(tests_dir, "pytest"))
test_module = os.path.basename(os.path.splitext(__file__)[0])
sim = os.getenv("SIM", "icarus")


@cocotb.test()
async def clock_design(dut):
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 10)


def run_simulation(sim):
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
        waves=True,
    )

    runner.test(
        hdl_toplevel_lang=hdl_toplevel_lang,
        hdl_toplevel=hdl_toplevel,
        gpi_interfaces=gpi_interfaces,
        test_module=test_module,
        test_args=sim_args,
        build_dir=sim_build,
        waves=True,
    )


@pytest.mark.simulator_required
@pytest.mark.skipif(
    sim not in ["icarus", "xcelium"],
    reason="Skipping test because it is only for Icarus or Xcelium simulators",
)
def test_wave_dump():
    run_simulation(sim=sim)
    if sim == "icarus":
        dumpfile_path = os.path.join(sim_build, f"{hdl_toplevel}.fst")
    elif sim == "xcelium":
        dumpfile_path = os.path.join(sim_build, "cocotb_waves.shm", "cocotb_waves.trn")
    else:
        raise RuntimeError("Not a supported simulator")
    assert os.path.exists(dumpfile_path)
