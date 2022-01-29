# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import pytest
import os

import cocotb
from cocotb.runner import get_runner
from cocotb.triggers import Timer

tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sim_build = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_build")


@cocotb.test()
async def cocotb_runner_test(dut):

    await Timer(1)

    WIDTH_IN = int(os.environ.get("WIDTH_IN", "8"))
    WIDTH_OUT = int(os.environ.get("WIDTH_OUT", "8"))

    assert WIDTH_IN == len(dut.data_in)
    assert WIDTH_OUT == len(dut.data_out)


@pytest.mark.parametrize("parameters", [{"WIDTH_IN": "8", "WIDTH_OUT": "16"}, {"WIDTH_IN": "16"}])
def test_runner(parameters):

    toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")

    verilog_sources = []
    vhdl_sources = []

    if toplevel_lang == "verilog":
        verilog_sources = [os.path.join(tests_dir, "designs", "runner", "runner.v")]
    else:
        vhdl_sources = [os.path.join(tests_dir, "designs", "runner", "runner.vhdl")]

    sim = os.getenv("SIM", "icarus")
    runner = get_runner(sim)()

    runner.build(
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        toplevel="runner",
        parameters=parameters,
        defines=["DEFINE=4"],
        includes=[os.path.join(tests_dir, "designs", "basic_hierarchy_module")],
        build_dir=sim_build + "/test_runner/" + "_".join(("{}={}".format(*i) for i in parameters.items())),
    )

    runner.test(
        python_search=[os.path.join(tests_dir, "pytest")],
        toplevel="runner",
        py_module="test_runner",
        extra_env=parameters,
    )
