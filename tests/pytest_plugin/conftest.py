# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Configuration for all tests."""

from __future__ import annotations

from pathlib import Path

from pytest import FixtureRequest, Parser, PytestPluginManager, fixture, hookimpl

from cocotb.clock import Clock
from cocotb_tools.pytest.hdl import HDL

PLUGIN: str = "cocotb_tools.pytest.plugin"
DESIGNS: Path = Path(__file__).parent.parent.resolve() / "designs"


@hookimpl(tryfirst=True)
def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    """Load pytest cocotb plugin in early stage of pytest when adding options to pytest.

    This will allow to automatically load plugin when invoking ``pytest`` with ``tests/pytest_plugin`` argument
    without need of providing additional ``-p cocotb_tools.pytest.plugin`` argument.

    Most users in their projects will load plugin by defining an entry point in ``pyproject.toml`` file:

    .. code:: toml

        [project.entry-points.pytest11]
        cocotb = "cocotb_tools.pytest.plugin"

    Args:
        parser: Instance of command line arguments parser used by pytest.
        pluginmanager: Instance of pytest plugin manager.
    """
    parser.addoption(
        "--hdl-toplevel-lang",
        choices=("vhdl", "verilog"),
        help="Select language for top level.",
    )

    if not pluginmanager.has_plugin(PLUGIN):
        pluginmanager.import_plugin(PLUGIN)  # import and register plugin


@fixture(name="sample_module")
def sample_module_fixture(hdl: HDL, request: FixtureRequest) -> HDL:
    """Define HDL design by adding HDL source files.

    To run cocotb tests for HDL design:

    .. code:: python

       import pytest
       from cocotb_tools.pytest.hdl import HDL

       @pytest.mark.cocotb
       def test_sample_module(sample_module: HDL) -> None:
           sample_module.test()

    Args:
        hdl: HDL design.

    Returns:
        Defined HDL design with added HDL source files.
    """
    hdl.toplevel = "sample_module"
    hdl_toplevel_lang: str | None = request.config.option.hdl_toplevel_lang

    if hdl_toplevel_lang == "vhdl" or hdl.simulator in ("nvc", "ghdl"):
        hdl.sources = (
            DESIGNS / "sample_module" / "sample_module_package.vhdl",
            DESIGNS / "sample_module" / "sample_module_1.vhdl",
            DESIGNS / "sample_module" / "sample_module.vhdl",
        )
    else:
        hdl.sources = (DESIGNS / "sample_module" / "sample_module.sv",)

    if hdl.simulator == "questa":
        hdl.build_args = ["+acc"]

    elif hdl.simulator == "xcelium":
        hdl.build_args = ["-v93"]

    elif hdl.simulator == "nvc":
        hdl.build_args = ["--std=08"]

    return hdl


@fixture(name="clock_generation", scope="session", autouse=True)
async def clock_generation_fixture(dut) -> None:
    """Generate clock for all tests using session scope."""
    dut.clk.value = 0

    Clock(dut.clk, 10, unit="ns").start(start_high=False)
