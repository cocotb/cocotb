import os
import sys
import tempfile
from pathlib import Path

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from cocotb_tools.runner import get_runner
from test_cocotb import (
    compile_args,
    gpi_interfaces,
    hdl_toplevel,
    hdl_toplevel_lang,
    sim_args,
    sim_build,
    sources,
    tests_dir,
)

sys.path.insert(0, os.path.join(tests_dir, "pytest"))
test_module = os.path.basename(os.path.splitext(__file__)[0])
sim = os.getenv("SIM", "icarus")


@cocotb.test()
async def clock_design(dut):
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())
    await ClockCycles(dut.clk, 10)


def run_simulation(sim, test_args=None):
    runner = get_runner(sim)
    runner.build(
        always=True,
        clean=True,
        sources=sources,
        hdl_toplevel=hdl_toplevel,
        build_dir=sim_build,
        build_args=compile_args,
        defines={"NODUMPFILE": 1},
        waves=True,
    )

    _test_args = sim_args
    if test_args is not None:
        _test_args.extend(test_args)

    runner.test(
        hdl_toplevel_lang=hdl_toplevel_lang,
        hdl_toplevel=hdl_toplevel,
        gpi_interfaces=gpi_interfaces,
        test_module=test_module,
        test_args=_test_args,
        build_dir=sim_build,
        waves=True,
    )


@pytest.mark.simulator_required
@pytest.mark.skipif(
    sim not in ["icarus", "verilator", "xcelium"],
    reason="Skipping test because it is only for Icarus, Verilator or Xcelium simulators",
)
def test_wave_dump():
    run_simulation(sim=sim)
    if sim == "icarus":
        dumpfile_path = os.path.join(sim_build, f"{hdl_toplevel}.fst")
    elif sim == "verilator":
        dumpfile_path = os.path.join(sim_build, "dump.vcd")
    elif sim == "xcelium":
        dumpfile_path = os.path.join(sim_build, "cocotb_waves.shm", "cocotb_waves.trn")
    else:
        raise RuntimeError("Not a supported simulator")
    assert os.path.exists(dumpfile_path)


@pytest.mark.simulator_required
@pytest.mark.skipif(
    sim not in ["verilator"],
    reason="Skipping test because it is only for Verilator simulators",
)
def test_named_wave_dump():
    temp_dir = Path(tempfile.mkdtemp())
    waves_file = temp_dir / "waves.vcd"
    run_simulation(sim=sim, test_args=["--trace-file", str(waves_file)])
    if sim not in ["verilator"]:
        raise RuntimeError("Not a supported simulator")
    assert waves_file.exists()
