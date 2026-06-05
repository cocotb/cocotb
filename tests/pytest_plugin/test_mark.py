# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :class:`cocotb_tools.pytest.mark` module."""

from __future__ import annotations

from pytest import MarkDecorator

from cocotb_tools.pytest import mark


def test_mark_cocotb_simulator() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_simulator` marker."""
    marker: MarkDecorator = mark.cocotb_simulator("verilator")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "verilator"
    assert marker.__doc__


def test_mark_cocotb_test_modules() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_test_modules` marker."""
    marker: MarkDecorator = mark.cocotb_test_modules("test_module_1", "test_module_2")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("test_module_1", "test_module_2")
    assert marker.__doc__


def test_mark_cocotb_toplevel() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_toplevel` marker."""
    marker: MarkDecorator = mark.cocotb_toplevel("top")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "top"
    assert marker.__doc__


def test_mark_cocotb_toplevel_lang() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_toplevel_lang` marker."""
    marker: MarkDecorator = mark.cocotb_toplevel_lang("verilog")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "verilog"
    assert marker.__doc__


def test_mark_cocotb_toplevel_library() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_toplevel_library` marker."""
    marker: MarkDecorator = mark.cocotb_toplevel_library("toplib")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "toplib"
    assert marker.__doc__


def test_mark_cocotb_timeout() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_timeout` marker."""
    marker: MarkDecorator = mark.cocotb_timeout(100, "ns")
    assert len(marker.args) == 0
    assert len(marker.kwargs) == 2
    assert marker.kwargs["duration"] == 100
    assert marker.kwargs["unit"] == "ns"
    assert marker.__doc__


def test_mark_cocotb_sources() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_sources` marker."""
    marker: MarkDecorator = mark.cocotb_sources("adder.sv", "alu.sv")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("adder.sv", "alu.sv")
    assert marker.__doc__


def test_mark_cocotb_defines() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_defines` marker."""
    marker: MarkDecorator = mark.cocotb_defines(
        DEFINE1="string", DEFINE2=1234, DEFINE3=1.25, DEFINE4=True
    )
    assert len(marker.args) == 0
    assert len(marker.kwargs) == 4
    assert marker.kwargs["DEFINE1"] == "string"
    assert marker.kwargs["DEFINE2"] == 1234
    assert marker.kwargs["DEFINE3"] == 1.25
    assert marker.kwargs["DEFINE4"]
    assert marker.__doc__


def test_mark_cocotb_parameters() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_parameters` marker."""
    marker: MarkDecorator = mark.cocotb_parameters(
        PARAM1="string", PARAM2=1234, PARAM3=1.25, PARAM4=True
    )
    assert len(marker.args) == 0
    assert len(marker.kwargs) == 4
    assert marker.kwargs["PARAM1"] == "string"
    assert marker.kwargs["PARAM2"] == 1234
    assert marker.kwargs["PARAM3"] == 1.25
    assert marker.kwargs["PARAM4"]
    assert marker.__doc__


def test_mark_cocotb_env() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_env` marker."""
    marker: MarkDecorator = mark.cocotb_env(
        ENV1="string", ENV2=1234, ENV3=1.25, ENV4=True
    )
    assert len(marker.args) == 0
    assert len(marker.kwargs) == 4
    assert marker.kwargs["ENV1"] == "string"
    assert marker.kwargs["ENV2"] == 1234
    assert marker.kwargs["ENV3"] == 1.25
    assert marker.kwargs["ENV4"]
    assert marker.__doc__


def test_mark_cocotb_includes() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_includes` marker."""
    marker: MarkDecorator = mark.cocotb_includes("incdir1", "incdir2")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("incdir1", "incdir2")
    assert marker.__doc__


def test_mark_cocotb_plusargs() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_plusargs` marker."""
    marker: MarkDecorator = mark.cocotb_plusargs("+arg1", "+arg2")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("+arg1", "+arg2")
    assert marker.__doc__


def test_mark_cocotb_timescale() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_timescale` marker."""
    marker: MarkDecorator = mark.cocotb_timescale("1ns/1ps")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "1ns/1ps"
    assert marker.__doc__


def test_mark_cocotb_random_seed() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_random_seed` marker."""
    marker: MarkDecorator = mark.cocotb_random_seed(1234)
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == 1234
    assert marker.__doc__


def test_mark_cocotb_build_dir() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_build_dir` marker."""
    marker: MarkDecorator = mark.cocotb_build_dir("build")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "build"
    assert marker.__doc__


def test_mark_cocotb_build_args() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_build_args` marker."""
    marker: MarkDecorator = mark.cocotb_build_args("arg1", "arg2")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("arg1", "arg2")
    assert marker.__doc__


def test_mark_cocotb_elab_args() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_elab_args` marker."""
    marker: MarkDecorator = mark.cocotb_elab_args("arg1", "arg2")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("arg1", "arg2")
    assert marker.__doc__


def test_mark_cocotb_sim_args() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_sim_args` marker."""
    marker: MarkDecorator = mark.cocotb_sim_args("arg1", "arg2")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("arg1", "arg2")
    assert marker.__doc__


def test_mark_cocotb_pre_cmd() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_pre_cmd` marker."""
    marker: MarkDecorator = mark.cocotb_pre_cmd("arg1", "arg2")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("arg1", "arg2")
    assert marker.__doc__


def test_mark_cocotb_library() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_library` marker."""
    marker: MarkDecorator = mark.cocotb_library("top")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "top"
    assert marker.__doc__


def test_mark_cocotb_gui() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_gui` marker."""
    marker: MarkDecorator = mark.cocotb_gui()
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0]
    assert marker.__doc__
    assert not mark.cocotb_gui(False).args[0]


def test_mark_cocotb_waves() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_waves` marker."""
    marker: MarkDecorator = mark.cocotb_waves()
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0]
    assert marker.__doc__
    assert not mark.cocotb_waves(False).args[0]


def test_mark_cocotb_verbose() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_verbose` marker."""
    marker: MarkDecorator = mark.cocotb_verbose()
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0]
    assert marker.__doc__
    assert not mark.cocotb_verbose(False).args[0]


def test_mark_cocotb_clean() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_clean` marker."""
    marker: MarkDecorator = mark.cocotb_clean()
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0]
    assert marker.__doc__
    assert not mark.cocotb_clean(False).args[0]


def test_mark_cocotb_always() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_always` marker."""
    marker: MarkDecorator = mark.cocotb_always()
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0]
    assert marker.__doc__
    assert not mark.cocotb_always(False).args[0]


def test_mark_cocotb_gpi_interfaces() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_gpi_interfaces` marker."""
    marker: MarkDecorator = mark.cocotb_gpi_interfaces("vpi", "vhpi")
    assert len(marker.args) == 2
    assert len(marker.kwargs) == 0
    assert marker.args == ("vpi", "vhpi")
    assert marker.__doc__


def test_mark_cocotb_test_filter() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_test_filter` marker."""
    marker: MarkDecorator = mark.cocotb_test_filter("^test_.*$")
    assert len(marker.args) == 1
    assert len(marker.kwargs) == 0
    assert marker.args[0] == "^test_.*$"
    assert marker.__doc__
