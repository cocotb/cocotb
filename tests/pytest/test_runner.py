# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from pathlib import Path

import find_libpython
import pytest

import cocotb
from cocotb.triggers import Timer
from cocotb.types import Logic, LogicArray
from cocotb_tools.runner import (
    VHDL,
    _as_tcl_value,
    as_sv_literal,
    as_vhdl_literal,
    get_runner,
)

pytestmark = pytest.mark.simulator_required

pytest_dir = Path(__file__).resolve().parent
tests_dir = pytest_dir.parent
sim_build = pytest_dir / "sim_build"
runner_design_dir = tests_dir / "designs" / "runner"
basic_hierarchy_module_dir = tests_dir / "designs" / "basic_hierarchy_module"
sys.path.insert(0, str(tests_dir / "pytest"))

sim = os.getenv(
    "SIM",
    "icarus" if os.getenv("TOPLEVEL_LANG", "verilog") == "verilog" else "nvc",
)

pre_cmd_sims = {
    "questa",
    "questa-qisqrun",
}


def test_empty_string():
    assert _as_tcl_value("") == ""


def test_special_char():
    assert _as_tcl_value("Test \n end\ttest\r") == "Test\\ \\n\\ end\\\ttest\\\r"


string_define_value = '"path/to/some/(random quote)/file.wow"'


def test_sv_literal_conversion():
    assert as_vhdl_literal(123) == "123"
    assert as_vhdl_literal(67.99) == "67.99"
    assert as_sv_literal(True) == "1'b1"
    assert as_sv_literal(False) == "1'b0"
    assert as_sv_literal(Logic("1")) == "1'b1"
    assert as_sv_literal(LogicArray("01XZ")) == "4'b01XZ"
    assert as_sv_literal("test") == '"test"'
    assert as_sv_literal("'\"\\\n") == '"\'\\"\\\\\\n"'

    for invalid_logic in ("W", "L", "H", "-", "U"):
        with pytest.raises(ValueError):
            as_sv_literal(LogicArray(invalid_logic))
        with pytest.raises(ValueError):
            as_sv_literal(Logic(invalid_logic))

    with pytest.raises(TypeError):
        as_sv_literal(object())
    with pytest.raises(TypeError):
        as_sv_literal(None)
    with pytest.raises(TypeError):
        as_sv_literal([])


def test_vhdl_literal_conversion():
    assert as_vhdl_literal(123) == "123"
    assert as_vhdl_literal(67.99) == "67.99"
    assert as_vhdl_literal(True) == "true"
    assert as_vhdl_literal(False) == "false"
    assert as_vhdl_literal(Logic("1")) == "1"
    assert as_vhdl_literal(LogicArray("UX01ZWHL-")) == "UX01ZWHL-"
    assert as_vhdl_literal("test") == '"test"'
    assert as_vhdl_literal("'\"\\") == '"\'""\\"'

    with pytest.raises(TypeError):
        as_vhdl_literal(object())
    with pytest.raises(TypeError):
        as_vhdl_literal(None)
    with pytest.raises(TypeError):
        as_vhdl_literal([])


@cocotb.test()
async def cocotb_runner_test(dut):
    await Timer(1, "ns")

    WIDTH_IN = int(os.environ.get("WIDTH_IN", "8"))
    WIDTH_OUT = int(os.environ.get("WIDTH_OUT", "8"))

    assert len(dut.data_in) == WIDTH_IN
    assert len(dut.data_out) == WIDTH_OUT


@pytest.mark.parametrize(
    "parameters", [{"WIDTH_IN": "8", "WIDTH_OUT": "16"}, {"WIDTH_IN": "16"}]
)
@pytest.mark.parametrize("clean_build", [False, True])
@pytest.mark.parametrize("pre_cmd", [["touch pre_cmd_test_file;"], None])
def test_runner(parameters, pre_cmd, clean_build):
    if sim not in pre_cmd_sims and pre_cmd is not None:
        pytest.skip("This simulator does not support pre_cmd")

    hdl_toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")
    vhdl_gpi_interfaces = os.getenv("VHDL_GPI_INTERFACE", None)

    if hdl_toplevel_lang == "verilog":
        sources = [runner_design_dir / "runner.sv"]
        gpi_interfaces = ["vpi"]
    else:
        sources = [runner_design_dir / "runner.vhdl"]
        gpi_interfaces = [vhdl_gpi_interfaces]

    runner = get_runner(sim)
    compile_args = [VHDL("-v93")] if sim == "xcelium" else []

    # Pre-make build directory and test file for clean build assertions
    build_dir_name = (
        "_".join(f"{key}={value}" for key, value in parameters.items())
        + ("_pre_cmd" if pre_cmd is not None else "")
        + ("_clean" if clean_build else "")
    )
    build_dir = sim_build / "test_runner" / build_dir_name
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "clean_test_file").touch()

    runner.build(
        sources=sources,
        hdl_toplevel="runner",
        parameters=parameters,
        defines={"DEFINE": 4, "DEFINE_STR": string_define_value},
        includes=[basic_hierarchy_module_dir],
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

    # Assert pre_cmd result. Questa flows only, at the moment
    if sim in pre_cmd_sims:
        if pre_cmd is not None:
            assert (build_dir / "pre_cmd_test_file").is_file()
        else:
            assert not (build_dir / "pre_cmd_test_file").is_file()

    # In case clean_build runner.build() must purge test directory completely,
    # with the test file inside
    if clean_build:
        assert not (build_dir / "clean_test_file").is_file()
    else:
        assert (build_dir / "clean_test_file").is_file()


def test_missing_libpython(monkeypatch):
    hdl_toplevel_lang = os.getenv("TOPLEVEL_LANG", "verilog")
    if hdl_toplevel_lang == "verilog":
        hdl_sources = [runner_design_dir / "runner.sv"]
        gpi_interfaces = ["vpi"]
    else:
        hdl_sources = [runner_design_dir / "runner.vhdl"]
        gpi_interfaces = [os.getenv("VHDL_GPI_INTERFACE", None)]

    sim_tool = os.getenv(
        "SIM",
        "icarus" if os.getenv("TOPLEVEL_LANG", "verilog") == "verilog" else "nvc",
    )
    sim_runner = get_runner(sim_tool)
    sim_params = {
        "WIDTH_IN": "8",
        "WIDTH_OUT": "8",
    }
    build_args = [VHDL("-v93")] if sim_tool == "xcelium" else []
    build_dir = sim_build / "test_missing_libpython"

    build_dir.mkdir(parents=True, exist_ok=True)

    sim_runner.build(
        sources=hdl_sources,
        hdl_toplevel="runner",
        parameters=sim_params,
        defines={"DEFINE": 4, "DEFINE_STR": string_define_value},
        includes=[basic_hierarchy_module_dir],
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
