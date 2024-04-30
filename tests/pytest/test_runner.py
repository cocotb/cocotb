# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys

import cocotb
import find_libpython
import pytest
from cocotb.triggers import Timer
from cocotb_tools.runner import get_runner

pytestmark = pytest.mark.simulator_required

tests_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sim_build = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sim_build")
sys.path.insert(0, os.path.join(tests_dir, "pytest"))


@cocotb.test()
async def cocotb_runner_test(dut):
    await Timer(1, "ns")

    WIDTH_IN = int(os.environ.get("WIDTH_IN", "8"))
    WIDTH_OUT = int(os.environ.get("WIDTH_OUT", "8"))

    assert WIDTH_IN == len(dut.data_in)
    assert WIDTH_OUT == len(dut.data_out)


@pytest.mark.parametrize(
    "parameters", [{"WIDTH_IN": "8", "WIDTH_OUT": "16"}, {"WIDTH_IN": "16"}]
)
@pytest.mark.parametrize("clean_build", [False, True])
@pytest.mark.parametrize("pre_cmd", [["touch pre_cmd_test_file;"], []])
def test_runner(parameters, pre_cmd, clean_build):
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    vhdl_gpi_interfaces = os.getenv("VHDL_GPI_INTERFACE", None)

    if hdl_toplevel_lang == "verilog":
        sources = [os.path.join(tests_dir, "designs", "runner", "runner.v")]
        gpi_interfaces = ["vpi"]
    else:
        sources = [os.path.join(tests_dir, "designs", "runner", "runner.vhdl")]
        gpi_interfaces = [vhdl_gpi_interfaces]

    sim = os.getenv("SIM", "icarus")
    runner = get_runner(sim)
    compile_args = []
    if sim == "xcelium":
        compile_args = ["-v93"]

    # Pre-make build directory and test file for clean build assertions
    build_dir = (
        sim_build
        + "/test_runner/"
        + "_".join("{}={}".format(*i) for i in parameters.items())
        + "_pre_cmd"
        + str(len(pre_cmd))
        + ("_clean" if clean_build else "")
    )
    os.makedirs(build_dir, exist_ok=True)
    open(build_dir + "/clean_test_file", "a").close()

    runner.build(
        sources=sources,
        hdl_toplevel="runner",
        parameters=parameters,
        defines={"DEFINE": 4},
        includes=[os.path.join(tests_dir, "designs", "basic_hierarchy_module")],
        build_args=compile_args,
        clean=clean_build,
        build_dir=build_dir,
    )

    runner.test(
        hdl_toplevel="runner",
        test_module="test_runner",
        pre_cmd=pre_cmd,
        gpi_interfaces=gpi_interfaces,
        extra_env=parameters,
    )

    # Assert pre_cmd result. Questa only, at the moment
    if sim == "questa":
        if pre_cmd:
            assert os.path.isfile(build_dir + "/pre_cmd_test_file")
        else:
            assert not os.path.isfile(build_dir + "/pre_cmd_test_file")

    # In case clean_build runner.build() must purge test directory completely,
    # with the test file inside
    if clean_build:
        assert not os.path.isfile(build_dir + "/clean_test_file")
    else:
        assert os.path.isfile(build_dir + "/clean_test_file")


def test_missing_libpython(monkeypatch):
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    if hdl_toplevel_lang == "verilog":
        hdl_sources = [os.path.join(tests_dir, "designs", "runner", "runner.v")]
        gpi_interfaces = ["vpi"]
    else:
        hdl_sources = [os.path.join(tests_dir, "designs", "runner", "runner.vhdl")]
        gpi_interfaces = [os.getenv("VHDL_GPI_INTERFACE", None)]

    sim_tool = os.getenv("SIM", "icarus")
    sim_runner = get_runner(sim_tool)
    sim_params = dict(
        WIDTH_IN="8",
        WIDTH_OUT="8",
    )
    build_args = ["-v93"] if sim_tool == "xcelium" else []
    build_dir = os.path.join(sim_build, "test_missing_libpython")

    os.makedirs(build_dir, exist_ok=True)

    sim_runner.build(
        sources=hdl_sources,
        hdl_toplevel="runner",
        parameters=sim_params,
        defines={"DEFINE": 4},
        includes=[os.path.join(tests_dir, "designs", "basic_hierarchy_module")],
        build_args=build_args,
        build_dir=build_dir,
    )

    def mock_find_libpython():
        return None

    monkeypatch.setattr(find_libpython, "find_libpython", mock_find_libpython)

    with pytest.raises(ValueError):
        sim_runner.test(
            hdl_toplevel="runner",
            test_module="test_runner",
            gpi_interfaces=gpi_interfaces,
            extra_env=sim_params,
        )
