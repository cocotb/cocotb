# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import random
from typing import Any

import pytest

import cocotb
from cocotb.handle import LogicArrayObject
from cocotb.triggers import Timer
from cocotb_tools.sim_versions import GhdlVersion, VerilatorVersion

LANGUAGE = os.getenv("TOPLEVEL_LANG").lower()
SIM = cocotb.SIM_NAME.lower()


@cocotb.test
@cocotb.skipif(LANGUAGE != "verilog")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed"),
        [
            ("enum", 32, True),
            ("byte", 8, True),
            ("shortint", 16, True),
            ("int", 32, True),
            ("longint", 64, True),
            ("integer", 32, True),
        ],
    )
)
@cocotb.parametrize(obj_type=("input", "signal"))
@cocotb.xfail(
    SIM.startswith("verilator")
    and VerilatorVersion(cocotb.SIM_VERSION) < VerilatorVersion("5.044"),
    reason="Verilator does not support signedness testing before v5.044",
    raises=RuntimeError,
)
async def test_int_verilog(
    verilog_dut: Any, name: str, width: int, is_signed: bool, obj_type: str
) -> None:
    """Test that Verilog integer types are handled correctly."""
    if name == "longint" and obj_type == "input" and SIM.startswith("xmsim"):
        # Xcelium uses different values for VPI constants and this causes longint ports to appear to return vpiRealNet.
        # TODO Replace with pytest.xfail call once supported.
        return
    obj_name = f"{name}_{obj_type}"
    handle = getattr(verilog_dut, obj_name)
    assert len(handle) == width
    assert handle.is_signed is is_signed

    # For backwards compatibility, LogicArrayObjects always use (INT_MIN, UINT_MAX) for bounds.
    # Some simulators discover integer handles as LogicArrayObjects.
    if isinstance(handle, LogicArrayObject):
        min_value = -(2 ** (width - 1))
        max_value = (2**width) - 1
    else:
        min_value = -(2 ** (width - 1)) if is_signed else 0
        max_value = (2 ** (width - 1)) - 1 if is_signed else (2**width) - 1

    for _ in range(100):
        handle.value = random.randint(min_value, max_value)
        await Timer(1)

    last_value = handle.value

    for max_value_test, min_value_test in zip(
        (
            max_value + 1,
            random.randint(max_value, 2 * max_value),
            2 * max_value,
            random.randint(2 * max_value, 10 * max_value),
        ),
        (
            min_value - 1,
            random.randint(2 * min_value, min_value),
            2 * min_value,
            random.randint(10 * min_value, 2 * min_value),
        ),
    ):
        with pytest.raises(ValueError):
            handle.value = max_value_test
        await Timer(1)
        assert handle.value == last_value

        with pytest.raises(ValueError):
            handle.value = min_value_test
        await Timer(1)
        assert handle.value == last_value


@cocotb.test
@cocotb.skipif(LANGUAGE != "vhdl")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed", "min_value", "max_value"),
        [
            ("integer", 32, True, -(2**31), 2**31 - 1),
            ("natural", 32, True, 0, 2**31 - 1),
            ("positive", 32, True, 1, 2**31 - 1),
            ("my_integer", 32, True, -100, 100),
        ],
    )
)
@cocotb.parametrize(obj_type=("input", "signal"))
@cocotb.xfail(
    SIM.startswith("ghdl") and GhdlVersion(cocotb.SIM_VERSION) < GhdlVersion("5.2"),
    reason="GHDL does not support signedness testing before 5.2",
)
async def test_integer_access_vhdl(
    vhdl_dut: Any,
    name: str,
    width: int,
    is_signed: bool,
    obj_type: str,
    min_value: int,
    max_value: int,
) -> None:
    """Test that VHDL integer types are handled correctly."""
    obj_name = f"{name}_{obj_type}"
    handle = getattr(vhdl_dut, obj_name)
    assert handle.is_signed is is_signed
    assert len(handle) == width

    # Use bounds of the specific subtype for random testing.
    # Otherwise we get fun range constraint violations which cause errors.
    for _ in range(100):
        handle.value = random.randint(min_value, max_value)
        await Timer(1)

    last_value = handle.value

    # For backwards compatibility, LogicArrayObjects always use (INT_MIN, UINT_MAX) for bounds.
    # Some simulators (GHDL) discover integer handles as LogicArrayObjects.
    if isinstance(handle, LogicArrayObject):
        min_value = -(2 ** (width - 1))
        max_value = (2**width) - 1
    else:
        min_value = -(2 ** (width - 1)) if is_signed else 0
        max_value = (2 ** (width - 1)) - 1 if is_signed else (2**width) - 1

    for max_value_test, min_value_test in zip(
        (
            max_value + 1,
            random.randint(max_value, 2 * max_value),
            2 * max_value,
            random.randint(2 * max_value, 10 * max_value),
        ),
        (
            min_value - 1,
            random.randint(2 * min_value, min_value),
            2 * min_value,
            random.randint(10 * min_value, 2 * min_value),
        ),
    ):
        with pytest.raises(ValueError):
            handle.value = max_value_test
        await Timer(1)
        assert handle.value == last_value

        with pytest.raises(ValueError):
            handle.value = min_value_test
        await Timer(1)
        assert handle.value == last_value
