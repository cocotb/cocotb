# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Compatibility layer between cocotb and pytest. Convert cocotb decorators to pytest markers."""

from __future__ import annotations

from collections.abc import Iterable
from inspect import iscoroutinefunction, signature
from typing import get_type_hints

from pytest import Function, Mark, mark

from cocotb._decorators import TestGenerator
from cocotb_tools.pytest.hdl import HDL

_MARKED: tuple[str, ...] = ("cocotb_runner", "cocotb_test")
"""List of pytest markers to mark cocotb test functions."""


def cocotb_decorator_as_pytest_marks(obj: TestGenerator) -> None:
    """Convert object decorated with cocotb decorator to ``@pytest.mark.*``.

    Args:
        obj: Object decorated with cocotb decorator like ``@cocotb.test``.
    """
    # Skip already converted object
    # This can happen when multiple cocotb runners are loading the same test module
    if getattr(obj.__func__, "__test__", False):
        return

    # Get pytest markers added at cocotb decorator level
    markers: list[Mark] = list(getattr(obj, "pytestmark", ()))

    # Replace @cocotb.parametrize(...) decorator with equivalent @pytest.mark.parametrize(...) markers
    # @cocotb.parametrize(x=[1, 2], y=[3, 4])
    # vvv
    # @pytest.parametrize("x", [1, 2])
    # @pytest.parametrize("y", [3, 4])
    for names, values in obj.options or ():
        if isinstance(names, str):
            markers.append(mark.parametrize(names, values).mark)
        else:
            markers.append(mark.parametrize(",".join(names), values).mark)

    # @cocotb.test(stage=...)
    if obj.stage:
        # Supported by external plugin: pytest-order
        markers.append(mark.order(obj.stage).mark)

    # @cocotb.test(skip=...)
    if obj.skip:
        markers.append(mark.skip().mark)

    # @cocotb.test(expect_fail=..., expect_error=...)
    if obj.expect_fail or obj.expect_error:
        markers.append(
            mark.xfail(
                raises=tuple(obj.expect_error) if obj.expect_error else None,
                strict=True,
            ).mark
        )

    # @cocotb.test(timeout=...)
    if obj.timeout:
        markers.append(
            mark.cocotb_timeout(duration=obj.timeout[0], unit=obj.timeout[1]).mark
        )

    # Get pytest markers added at test function level
    markers.extend(getattr(obj.__func__, "pytestmark", ()))

    # Add missing @pytest.mark.cocotb_test marker to test function
    if not any(marker.name == "cocotb_test" for marker in markers):
        markers.append(mark.cocotb_test().mark)

    # Add pytest markers to test function and decorator
    setattr(obj.__func__, "pytestmark", markers)
    setattr(obj, "pytestmark", markers)

    # Mark test function with @cocotb.test decorator as test for pytest
    mark_as_test(obj)


def is_marked_as_cocotb(obj: object) -> bool:
    """Check if object is marked with :deco:`!pytest.mark.cocotb_runner` or :deco:`!pytest.mark.cocotb_test`.

    Args:
        obj: Collected item by the pytest Python collector (:class:`pytest.Module` or :class:`pytest.Class`).

    Returns:
        :data:`True` if collected item is already marked with :deco:`!pytest.mark.cocotb_runner` or
        :deco:`!pytest.mark.cocotb_test` decorator. Otherwise :data:`False`.
    """
    # Get list of pytest markers added to test function
    markers: Iterable[Mark] | None = getattr(obj, "pytestmark", None)

    # Check if object was marked with @pytest.mark.cocotb_runner or @pytest.mark.cocotb_test
    return any(marker.name in _MARKED for marker in markers or ())


def mark_as_test(obj: object) -> None:
    """Mark object as test for pytest.

    Args:
        obj: Collected item by the pytest Python collector (:class:`pytest.Module` or :class:`pytest.Class`).
    """
    # Needed to tell pytest that collected object is a test function
    setattr(obj, "__test__", True)

    if hasattr(obj, "__func__"):
        # Needed to tell pytest that wrapped function in collected object is a test function
        setattr(obj.__func__, "__test__", True)


def is_cocotb_runner(item: Function) -> bool:
    """Check if test function is a cocotb runner.

    Args:
        item: Collected item as pytest test function.

    Returns:
        :data:`True` if collected item is a cocotb runner. Otherwise :data:`False`.
    """
    if not iscoroutinefunction(item.function):
        if item.get_closest_marker("cocotb_runner"):
            return True

        # Determine based on used HDL fixture in arguments, fixture name is irrelevant, detect based on argument type
        for name, type_hint in get_type_hints(item.function).items():
            if name in item.fixturenames and type_hint and issubclass(type_hint, HDL):
                return True

    return False


def is_cocotb_test(item: Function) -> bool:
    """Check if test function is a cocotb test.

    Args:
        item: Collected item as pytest test function.

    Returns:
        :data:`True` if collected item is a cocotb test. Otherwise :data:`False`.
    """
    return iscoroutinefunction(item.function) and (
        item.get_closest_marker("cocotb_test") is not None
        or "dut" in signature(item.function).parameters
    )


def pre_process_collected_item(obj: object) -> None:
    """Pre-process collected item.

    Args:
        obj: Collected item by the pytest Python collector (:class:`pytest.Module` or :class:`pytest.Class`).
    """
    if isinstance(obj, TestGenerator):
        # Convert @cocotb.* decorators to @pytest.mark.* markers
        cocotb_decorator_as_pytest_marks(obj)

    elif is_marked_as_cocotb(obj):
        # Mark object with @pytest.mark.cocotb_runner or @pytest.mark.cocotb_test as test
        mark_as_test(obj)
