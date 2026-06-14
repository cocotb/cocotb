# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :mod:`cocotb_tools.pytest` module."""

from __future__ import annotations

import os
import shlex
from argparse import Namespace
from pathlib import Path

from pytest import (
    FixtureRequest,
    MonkeyPatch,
    Parser,
    Pytester,
    PytestPluginManager,
    fixture,
    hookimpl,
)

from cocotb_tools.pytest._simulator import find_simulator
from cocotb_tools.runner import get_runner

#: List of plugin to enable
PLUGINS: tuple[str, ...] = (
    "pytester",
    "cocotb_tools.pytest.plugin",
)

TESTS_DIR: Path = Path(__file__).parent.parent.resolve()
"""Absolute path to the tests directory."""

DESIGNS_DIR: Path = TESTS_DIR / "designs"
"""Absolute path to the directory with HDL design samples."""

TEST_COCOTB_DIR: Path = TESTS_DIR / "test_cases" / "test_cocotb"
"""Absolute path to the test_cocotb directory that contains cocotb tests run for HDL design samples."""


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
    for plugin in PLUGINS:
        if not pluginmanager.has_plugin(plugin):
            pluginmanager.import_plugin(plugin)  # import and register plugin


@fixture
def designs_dir() -> Path:
    """Absolute path to directory with HDL design samples."""
    return DESIGNS_DIR


@fixture
def test_cocotb_dir() -> Path:
    """Absolute path to directory with cocotb tests."""
    return TEST_COCOTB_DIR


@fixture(name="pytester")
def pytester_fixture(
    pytester: Pytester, request: FixtureRequest, monkeypatch: MonkeyPatch
) -> Pytester:
    """Setup :class:`pytest.Pytester` fixture."""
    option: Namespace = request.config.option

    simulator: str | None = option.cocotb_simulator
    language: str | None = option.cocotb_toplevel_lang
    gpi_interfaces: list[str] = option.cocotb_gpi_interfaces

    if not simulator or simulator == "auto":
        simulator = find_simulator(languages=language)

    if simulator:
        supported_gpi_interfaces: dict[str, list[str]] = get_runner(
            simulator
        ).supported_gpi_interfaces

        if not language or language == "auto":
            # Pick the first supported language by HDL simulator
            language = list(supported_gpi_interfaces)[0]

        if not gpi_interfaces:
            gpi_interfaces = supported_gpi_interfaces[language]

    addopts: list[str] = [
        "--verbose",
        "--capture=no",
        "--strict-markers",
        "-p",
        "cocotb_tools.pytest.plugin",
    ]

    lines: list[str] = [
        "[pytest]",
        "addopts = " + shlex.join(addopts),
    ]

    if simulator:
        lines.append(f"cocotb_simulator = {simulator}")

    if language:
        lines.append(f"cocotb_toplevel_lang = {language}")

    if gpi_interfaces:
        lines.append(f"cocotb_gpi_interfaces = {' '.join(gpi_interfaces)}")

    # It creates the 'pytest.ini' file
    # https://docs.pytest.org/en/stable/reference/customize.html#pytest-ini
    pytester.makefile(".ini", pytest="\n".join(lines))

    for name in os.environ:
        if any(map(name.startswith, ("COCOTB", "PYGPI", "GPI"))):
            monkeypatch.delenv(name, raising=False)

    # Create a SystemVerilog top level module example
    pytester.makefile(
        ".sv",
        top="""
        module top #(
            WIDTH = 8
        ) (
            input i_clk,
            input i_rst,
            input [WIDTH-1:0] i_data,
            output logic [WIDTH-1:0] o_data
        );
            always_ff @(posedge i_clk) begin
                if (i_rst == 1'b1) begin
                    o_data <= '0;
                end else begin
                    o_data <= i_data;
                end
            end
        endmodule
        """,
    )

    # Create a VHDL top level module example
    pytester.makefile(
        ".vhd",
        top="""
        library ieee;
        use ieee.std_logic_1164.all;

        entity top is generic (
            WIDTH: natural := 8
        );
        port (
            i_clk : in std_logic;
            i_rst : in std_logic;
            i_data : in std_logic_vector(WIDTH-1 downto 0);
            o_data : out std_logic_vector(WIDTH-1 downto 0)
        );
        end top;

        architecture rtl of top is begin
            process(i_clk) begin
                if (rising_edge(i_clk)) then
                    if i_rst = '1' then
                        o_data <= (others => '0');
                    else
                        o_data <= i_data;
                    end if;
                end if;
            end process;
        end rtl;
        """,
    )

    pytester.makeconftest("""
        from pathlib import Path
        from pytest import fixture
        from cocotb_tools.pytest.dut import Dut

        DIR: Path = Path(__file__).parent.resolve()

        @fixture(name="dut")
        def dut_fixture(dut: Dut) -> Dut:
            if dut.toplevel_lang == "verilog":
                dut.sources += [DIR / "top.sv"]

            elif dut.toplevel_lang == "vhdl":
                dut.sources += [DIR / "top.vhd"]

            return dut
        """)

    return pytester
