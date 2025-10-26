# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Configuration for all tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from pytest import FixtureRequest, Parser, PytestPluginManager, fixture, hookimpl

from cocotb.clock import Clock
from cocotb.triggers import FallingEdge
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
    if not pluginmanager.has_plugin(PLUGIN):
        pluginmanager.import_plugin(PLUGIN)  # import and register plugin


@fixture(name="hdl_build", scope="session")
def hdl_build_fixture(request: FixtureRequest) -> HDL:
    """Build HDL design.

    To run cocotb tests for HDL design:

    .. code:: python

       import pytest
       from cocotb_tools.pytest.hdl import HDL

       @pytest.mark.cocotb
       def test_sample_module(hdl: HDL) -> None:
           hdl.test()

    Args:
        request: Fixture request.

    Returns:
        Compiled HDL design.
    """
    hdl_toplevel_lang: str = request.config.option.cocotb_hdl_toplevel_lang
    hdl: HDL = HDL(request)

    if hdl_toplevel_lang == "vhdl" or hdl.simulator in ("ghdl", "nvc"):
        sources = (
            DESIGNS / "sample_module" / "sample_module_package.vhdl",
            DESIGNS / "sample_module" / "sample_module_1.vhdl",
            DESIGNS / "sample_module" / "sample_module.vhdl",
        )
    else:
        sources = (DESIGNS / "sample_module" / "sample_module.sv",)

    hdl.build(sources=sources)

    return hdl


@fixture(name="hdl")
def hdl_fixture(hdl_build: HDL, request: FixtureRequest) -> HDL:
    return hdl_build.from_request(request)


@fixture(name="clock_generation", scope="session")
async def clock_generation_fixture(dut) -> None:
    """Generate clock for all tests using session scope."""
    dut.clk.value = 0

    Clock(dut.clk, 10, unit="ns").start(start_high=False)


@fixture(name="sample_module")
async def sample_module_fixture(dut, clock_generation) -> Generator[None, None]:
    """Setup/teardown sample module."""
    # Test setup (executed before test)
    dut.stream_in_valid.value = 0
    dut.stream_in_data.value = 0
    dut.stream_out_ready.value = 0

    for _ in range(2):
        await FallingEdge(dut.clk)

    yield  # Calling test

    # Test teardown (executed after test)
    dut.stream_in_valid.value = 0
    dut.stream_in_data.value = 0
    dut.stream_out_ready.value = 0

    # NOTE: Without it, Icarus simulator will crash with unexpected segmentation fault
    # at the end of the simulation. This also happen using built-in regression manager.
    # All other HDL simulators are fine, only Icarus is buggy
    await FallingEdge(dut.clk)
