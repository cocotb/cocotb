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
from cocotb.types import LogicArray
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

        def check(actual: LogicArray, expected: int) -> bool:
            if expected >= 0:
                return actual.to_unsigned() == expected
            else:
                return actual.to_signed() == expected

    else:
        min_value = -(2 ** (width - 1)) if is_signed else 0
        max_value = (2 ** (width - 1)) - 1 if is_signed else (2**width) - 1

        def check(actual: int, expected: int) -> bool:
            return actual == expected

    for _ in range(100):
        exp_value = random.randint(min_value, max_value)
        handle.value = exp_value
        await Timer(1)
        assert check(handle.value, exp_value)

    handle.value = 67
    await Timer(1)

    for value in (
        # Above maximum value
        max_value + 1,
        random.randint(max_value + 1, 2 * max_value),
        2 * max_value,
        random.randint(2 * max_value, 10 * max_value),
        10 * max_value,
        # Below minimum value
        min_value - 1,
        random.randint(2 * min_value, min_value - 1),
        2 * min_value,
        random.randint(10 * min_value, 2 * min_value),
        10 * min_value,
    ):
        cocotb.log.info(f"Testing value={value}")

        with pytest.raises(ValueError):
            handle.value = value

        # ensure it wasn't applied
        await Timer(1)
        assert handle.value == 67


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

    # For backwards compatibility, LogicArrayObjects always use (INT_MIN, UINT_MAX) for bounds.
    # Some simulators (GHDL) discover integer handles as LogicArrayObjects.
    if isinstance(handle, LogicArrayObject):

        def check(actual: LogicArray, expected: int) -> bool:
            if expected >= 0:
                return actual.to_unsigned() == expected
            else:
                return actual.to_signed() == expected

    else:

        def check(actual: int, expected: int) -> bool:
            return actual == expected

    # Use bounds of the specific subtype for random testing.
    # Otherwise we get fun range constraint violations which cause errors.
    for _ in range(100):
        exp_value = random.randint(min_value, max_value)
        handle.value = exp_value
        await Timer(1)
        assert check(handle.value, exp_value)

    # For backwards compatibility, LogicArrayObjects always use (INT_MIN, UINT_MAX) for bounds.
    # Some simulators (GHDL) discover integer handles as LogicArrayObjects.
    if isinstance(handle, LogicArrayObject):
        min_value = -(2 ** (width - 1))
        max_value = (2**width) - 1
    else:
        min_value = -(2 ** (width - 1)) if is_signed else 0
        max_value = (2 ** (width - 1)) - 1 if is_signed else (2**width) - 1

    handle.value = 67
    await Timer(1)

    for value in (
        # Above maximum value
        max_value + 1,
        random.randint(max_value + 1, 2 * max_value),
        2 * max_value,
        random.randint(2 * max_value, 10 * max_value),
        10 * max_value,
        # Below minimum value
        min_value - 1,
        random.randint(2 * min_value, min_value - 1),
        2 * min_value,
        random.randint(10 * min_value, 2 * min_value),
        10 * min_value,
    ):
        cocotb.log.info(f"Testing value={value}")

        with pytest.raises(ValueError):
            handle.value = value

        # ensure it wasn't applied
        await Timer(1)
        assert handle.value == 67
