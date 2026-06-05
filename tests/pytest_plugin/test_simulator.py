# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test the :mod:`cocotb_tools.pytest._simulator` module."""

from __future__ import annotations

from pytest import MonkeyPatch

from cocotb_tools.pytest._simulator import (
    are_languages_supported,
    detect_language,
    detect_languages,
    find_simulator,
    get_supported_languages,
)
from cocotb_tools.runner import VHDL, Verilog


def test_simulator_detect_language() -> None:
    """Test the :func:`cocotb_tools.pytest._simulator.detect_language` function."""
    assert detect_language("top.v") == "verilog"
    assert detect_language("top.sv") == "verilog"
    assert detect_language(Verilog("top.v")) == "verilog"
    assert detect_language("top.vhd") == "vhdl"
    assert detect_language("top.vhdl") == "vhdl"
    assert detect_language(VHDL("top.vhdl")) == "vhdl"
    assert detect_language("top.xyz") is None


def test_simulator_detect_languages() -> None:
    """Test the :func:`cocotb_tools.pytest._simulator.detect_languages` function."""
    for sources, languages in (
        (
            ("top.v",),
            ("verilog",),
        ),
        (
            ("top.vhd",),
            ("vhdl",),
        ),
        (
            ("top.v", "top.vhd"),
            ("verilog", "vhdl"),
        ),
    ):
        assert sorted(detect_languages(sources)) == sorted(languages)


def test_simulator_are_languages_supported() -> None:
    """Test the :func:`cocotb_tools.pytest._simulator.are_languages_supported` function."""
    for simulator in ("nvc", "ghdl"):
        assert are_languages_supported(simulator, None)
        assert are_languages_supported(simulator, "auto")
        assert are_languages_supported(simulator, ())
        assert are_languages_supported(simulator, "vhdl")
        assert are_languages_supported(simulator, ("vhdl",))
        assert not are_languages_supported(simulator, "verilog")
        assert not are_languages_supported(simulator, ("verilog",))
        assert not are_languages_supported(simulator, ("verilog", "vhdl"))

    for simulator in ("verilator", "icarus"):
        assert are_languages_supported(simulator, None)
        assert are_languages_supported(simulator, "auto")
        assert are_languages_supported(simulator, ())
        assert are_languages_supported(simulator, "verilog")
        assert are_languages_supported(simulator, ("verilog",))
        assert not are_languages_supported(simulator, "vhdl")
        assert not are_languages_supported(simulator, ("vhdl",))
        assert not are_languages_supported(simulator, ("vhdl", "verilog"))

    for simulator in ("questa", "xcelium"):
        assert are_languages_supported(simulator, None)
        assert are_languages_supported(simulator, "auto")
        assert are_languages_supported(simulator, ())
        assert are_languages_supported(simulator, "vhdl")
        assert are_languages_supported(simulator, "verilog")
        assert are_languages_supported(simulator, ("vhdl",))
        assert are_languages_supported(simulator, ("verilog",))
        assert are_languages_supported(simulator, ("vhdl", "verilog"))
        assert are_languages_supported(simulator, ("verilog", "vhdl"))


def test_simulator_find_simulator_none(monkeypatch: MonkeyPatch) -> None:
    """Test the :func:`cocotb_tools.pytest._simulator.find_simulator` function."""
    monkeypatch.delenv("PATH", raising=False)

    for simulator in ("nvc", "ghdl", "verilator", "icarus", "questa", "xcelium"):
        assert find_simulator(simulator) is None


def test_simulator_get_supported_languages() -> None:
    """Test the :func:`cocotb_tools.pytest._simulator.get_supported_languages` function."""
    for simulator in (None, "", "auto", "unknown"):
        assert get_supported_languages(simulator) == []

    for simulator in ("nvc", "ghdl"):
        assert get_supported_languages(simulator) == ["vhdl"]

    for simulator in ("verilator", "icarus"):
        assert get_supported_languages(simulator) == ["verilog"]

    for simulator in ("questa", "xcelium"):
        assert sorted(get_supported_languages(simulator)) == ["verilog", "vhdl"]
