import os
import sys
import tempfile

import pytest
from test_cocotb import (
    compile_args,
    gpi_interfaces,
    hdl_toplevel,
    hdl_toplevel_lang,
    sim,
    sim_args,
    sim_build,
    tests_dir,
    verilog_sources,
    vhdl_sources,
)

from cocotb.runner import get_runner
from cocotb.utils import _get_log_time_scale

sys.path.insert(0, os.path.join(tests_dir, "pytest"))

cocotb_test_contents = """
import cocotb
from cocotb.utils import _get_simulator_precision

@cocotb.test()
async def check_timescale(dut):
    assert _get_simulator_precision() == {precision}
"""


@pytest.mark.simulator_required
@pytest.mark.skipif(
    os.getenv("SIM", "icarus") != "icarus",
    reason="Currently only Icarus simulator supports timescale setting when using Cocotb runner",
)
@pytest.mark.parametrize("precision", ["fs", "ps", "ns", "us", "ms", "s"])
def test_precision(precision):
    build_dir = os.path.join(sim_build, "test_timescale_{}".format(precision))

    timescale = (f"1{precision}", f"1{precision}")
    precision_log = _get_log_time_scale(precision if precision != "s" else "sec")

    with tempfile.TemporaryDirectory() as d:
        sys.path.insert(0, d)
        test_module_path = os.path.join(d, "test_precision.py")
        test_module = os.path.basename(os.path.splitext(test_module_path)[0])
        with open(test_module_path, "w") as f:
            f.write(cocotb_test_contents.format(precision=precision_log))
            f.flush()

        runner = get_runner(sim)
        runner.build(
            always=True,
            clean=True,
            verilog_sources=verilog_sources,
            vhdl_sources=vhdl_sources,
            hdl_toplevel=hdl_toplevel,
            build_dir=build_dir,
            build_args=compile_args,
            defines={"NOTIMESCALE": 1},
            timescale=timescale,
        )

        runner.test(
            hdl_toplevel_lang=hdl_toplevel_lang,
            hdl_toplevel=hdl_toplevel,
            gpi_interfaces=gpi_interfaces,
            test_module=test_module,
            test_args=sim_args,
            build_dir=build_dir,
        )
