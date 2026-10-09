# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import random
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import pytest

import cocotb
from cocotb.handle import EnumObject, IntegerObject, LogicArrayObject, PackedObject
from cocotb.triggers import Timer
from cocotb.types import LogicArray
from cocotb_tools.sim_versions import GhdlVersion, VerilatorVersion

LANGUAGE = os.getenv("TOPLEVEL_LANG").lower()
SIM = cocotb.SIM_NAME.lower()


@contextmanager
def assert_xfail(
    condition: bool, raises: type[BaseException], reason: str
) -> Generator[None, None, None]:
    """Calls pytest.xfail if the body raises the exception and the condition is met.

    If the condition is met and nothing is raised, this will raise an :exc:`AssertionError`.
    If the body fails and the condition is not met, the exception will be propagated.
    """
    try:
        yield
    except raises:
        if condition:
            pytest.xfail(reason)
        else:
            raise
    else:
        if condition:
            raise AssertionError(f"Did not fail as expected: {reason}")


@cocotb.test
@cocotb.skipif(LANGUAGE != "verilog")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed"),
        [
            ("enum", 32, True),
            ("enum_byte", 8, True),
            ("enum_longint", 64, True),
            ("enum_uint", 32, False),
            ("enum_ulongint", 64, False),
            ("byte", 8, True),
            ("byte_unsigned", 8, False),
            ("shortint", 16, True),
            ("shortint_unsigned", 16, False),
            ("int", 32, True),
            ("int_unsigned", 32, False),
            ("longint", 64, True),
            ("longint_unsigned", 64, False),
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
    verilog_dut: Any,
    name: str,
    width: int,
    is_signed: bool,
    obj_type: str,
) -> None:
    """Test that Verilog integer types are handled correctly."""
    obj_name = f"{name}_{obj_type}"
    handle = getattr(verilog_dut, obj_name)
    with assert_xfail(
        condition=name == "longint" and obj_type == "input" and SIM.startswith("xmsim"),
        raises=RuntimeError,
        reason="Xcelium reports longint input ports as RealObject",
    ):
        assert isinstance(
            handle,
            (EnumObject if name.startswith("enum") else IntegerObject)
            # Verilog simulators could return the object simply as vpiNet or vpiReg which would get mapped to PackedObject
            | PackedObject,
        )
    assert len(handle) == width
    assert handle.is_signed is is_signed

    # For backwards compatibility, PackedObjects always use (INT_MIN, UINT_MAX) for bounds.
    # Some simulators discover integer handles as PackedObjects.
    if isinstance(handle, PackedObject):
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

    for exp_value in (
        # Deliberately test the boundary values.
        [max_value, min_value]
        # And some random values within the range
        + [random.randint(min_value, max_value) for _ in range(100)]
    ):
        handle.value = exp_value
        await Timer(1)
        assert check(handle.value, exp_value)

    valid_value = random.randint(min_value, max_value)

    handle.value = valid_value
    await Timer(1)

    for value in (
        # Above maximum value
        max_value + random.randint(max_value, 2 * max_value),
        max_value + random.randint(1, max_value),
        max_value + 1,
        # Below minimum value
        min_value - 1,
        min_value - random.randint(1, max_value),
        min_value - random.randint(max_value, 2 * max_value),
    ):
        cocotb.log.info(f"Testing value={value}")

        with pytest.raises(ValueError):
            handle.value = value

        # ensure it wasn't applied
        await Timer(1)
        assert handle.value == valid_value


@cocotb.test
@cocotb.skipif(LANGUAGE != "vhdl")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed", "min_value", "max_value"),
        [
            ("enum", None, False, 0, 2),
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
    width: int | None,
    is_signed: bool,
    obj_type: str,
    min_value: int,
    max_value: int,
) -> None:
    """Test that VHDL integer and enumeration types are handled correctly."""
    obj_name = f"{name}_{obj_type}"

    with assert_xfail(
        condition=name == "enum" and SIM.startswith("ghdl"),
        raises=AttributeError,
        reason="GHDL does not support enum access",
    ):
        handle = getattr(vhdl_dut, obj_name)

    assert isinstance(handle, EnumObject if name == "enum" else IntegerObject)
    assert handle.is_signed is is_signed
    if width is None:
        # The width of an enumeration ordinal depends on the simulator interface.
        width = len(handle)
    assert len(handle) == width

    # For backwards compatibility, LogicArray/PackedObjects always use (INT_MIN, UINT_MAX) for bounds.
    # Some simulators (GHDL) discover integer handles as LogicArray/PackedObjects.
    if isinstance(handle, (LogicArrayObject, PackedObject)):

        def check(actual: LogicArray, expected: int) -> bool:
            if expected >= 0:
                return actual.to_unsigned() == expected
            else:
                return actual.to_signed() == expected

    else:

        def check(actual: int, expected: int) -> bool:
            return actual == expected

    # For backwards compatibility, LogicArray always use (INT_MIN, UINT_MAX) for bounds.
    # Some simulators (GHDL) discover integer handles as LogicArray.
    if isinstance(handle, LogicArrayObject):
        min_value = -(2 ** (width - 1))
        max_value = (2**width) - 1
    else:
        min_value = -(2 ** (width - 1)) if is_signed else 0
        max_value = (2 ** (width - 1)) - 1 if is_signed else (2**width) - 1

    for exp_value in (
        # Deliberately test the boundary values.
        [max_value, min_value]
        # And some random values within the range
        + [random.randint(min_value, max_value) for _ in range(100)]
    ):
        handle.value = exp_value
        await Timer(1)
        assert check(handle.value, exp_value)

    valid_value = random.randint(min_value, max_value)
    handle.value = valid_value
    await Timer(1)

    for value in (
        # Above maximum value
        max_value + random.randint(max_value, 2 * max_value),
        max_value + random.randint(1, max_value),
        max_value + 1,
        # Below minimum value
        min_value - 1,
        min_value - random.randint(1, max_value),
        min_value - random.randint(max_value, 2 * max_value),
    ):
        cocotb.log.info(f"Testing value={value}")

        with pytest.raises(ValueError):
            handle.value = value

        # ensure it wasn't applied
        await Timer(1)
        assert check(handle.value, valid_value)
