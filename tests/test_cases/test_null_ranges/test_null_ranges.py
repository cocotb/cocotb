# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import Any

import pytest

import cocotb
from cocotb.types import LogicArray, Range

is_questa_vhpi = (
    cocotb.SIM_NAME.lower().startswith("modelsim")
    and os.environ["VHDL_GPI_INTERFACE"] == "vhpi"
)
is_xcelium = cocotb.SIM_NAME.lower().startswith("xmsim")
is_riviera = cocotb.SIM_NAME.lower().startswith("riviera")
is_ghdl = cocotb.SIM_NAME.lower().startswith("ghdl")


@cocotb.parametrize(
    (
        ("signal_name", "high", "direction", "low"),
        (
            ("null_vector_port_to", 10, "to", 4),
            ("null_vector_port_downto", -1, "downto", 0),
            ("null_vector_signal_to", 10, "to", 4),
            ("null_vector_signal_downto", -1, "downto", 0),
        ),
    )
)
@cocotb.xfail(
    is_questa_vhpi,
    reason="Questa does not return correct direction for ranges (gh-4236)",
)
@cocotb.xfail(
    is_ghdl,
    raises=Exception,
    reason="GHDL cannot find null-ranged vectors (gh-5458)",
)
@cocotb.test
async def test_null_vector(
    dut: Any,
    signal_name: str,
    high: int,
    direction: str,
    low: int,
) -> None:
    handle = getattr(dut, signal_name)
    assert handle.range == Range(high, direction, low)
    assert len(handle) == 0
    assert handle.value == LogicArray([])
    assert handle.value.range == Range(high, direction, low)
    with pytest.raises(ValueError):
        handle.value = 0x1


@cocotb.parametrize(
    (
        ("signal_name", "high", "direction", "low"),
        (
            ("null_array_port_to", 0, "to", -1),
            ("null_array_port_downto", -7, "downto", 0),
            ("null_array_signal_to", 0, "to", -1),
            ("null_array_signal_downto", -7, "downto", 0),
        ),
    )
)
@cocotb.xfail(
    is_questa_vhpi,
    reason="Questa does not return correct direction for ranges (gh-4236)",
)
@cocotb.xfail(
    is_ghdl,
    reason="GHDL uses VPI and cannot represent null-ranged objects, the ranges will mismatch",
)
@cocotb.test
async def test_null_array(
    dut: Any,
    signal_name: str,
    high: int,
    direction: str,
    low: int,
) -> None:
    handle = getattr(dut, signal_name)
    assert handle.range == Range(high, direction, low)
    assert len(handle) == 0
    assert handle.value == []
    assert len(handle.value) == 0
    assert handle.value.range == Range(high, direction, low)
    with pytest.raises(ValueError):
        handle.value = [1, 2, 3, 4]


@cocotb.parametrize(
    (
        ("signal_name", "high", "direction", "low"),
        (
            ("null_string_port_to", 3, "to", -2),
            ("null_string_port_downto", 0, "downto", 7),
            ("null_string_signal_to", 3, "to", -2),
            ("null_string_signal_downto", 0, "downto", 7),
        ),
    )
)
@cocotb.xfail(
    is_questa_vhpi,
    raises=AttributeError,
    reason="Questa discovers null-ranged strings as vhpiSigDeclK and vhpiPortDeclK (gh-5461)",
)
@cocotb.xfail(
    is_xcelium,
    raises=AttributeError,
    reason="Xcelium discovers null-ranged strings as vhpiSigDeclK and vhpiPortDeclK (gh-5460)",
)
@cocotb.skipif(
    is_riviera,
    reason="Riviera crashes when accessing null-ranged string objects (gh-5459)",
)
@cocotb.xfail(
    is_ghdl,
    reason="GHDL uses VPI and cannot represent null-ranged objects, the ranges will mismatch",
)
@cocotb.test
async def test_null_string(
    dut: Any,
    signal_name: str,
    high: int,
    direction: str,
    low: int,
) -> None:
    handle = getattr(dut, signal_name)
    assert handle.range == Range(high, direction, low)
    assert len(handle) == 0
    assert handle.value == b""
