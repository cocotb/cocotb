# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Compatibility layer between cocotb and pytest. Convert cocotb decorators to pytest markers."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pytest import Class, Mark, Module, mark

from cocotb._decorators import Test, TestGenerator
from cocotb.simtime import TimeUnit


def is_cocotb_decorator(obj: object) -> bool:
    """Check if provided object was decorated with cocotb decorator."""
    return isinstance(obj, (Test, TestGenerator))


def cocotb_decorator_as_pytest_marks(
    collector: Module | Class, name: str, obj: object
) -> object:
    """Convert object decorated with cocotb decorator to ``@pytest.mark.*``.

    Args:
        collector: Pytest collector like Python Class or Module.
        name: Name of object.
        obj: Object decorated with cocotb decorator like ``@cocotb.test``.

    Returns:
        Unwrapped decorated object with added pytest marks.
    """
    if isinstance(obj, Test):
        return _as_pytest_marks(
            collector,
            name,
            obj.func,
            timeout=obj.timeout,
            expect_fail=obj.expect_fail,
            expect_error=obj.expect_error,
            skip=obj.skip,
            stage=obj.stage,
        )

    if isinstance(obj, TestGenerator):
        return _as_pytest_marks(
            collector,
            name,
            obj.func,
            timeout=obj.timeout,
            expect_fail=obj.expect_fail,
            expect_error=obj.expect_error,
            skip=obj.skip,
            stage=obj.stage,
            options=obj.options,
        )

    return obj


def _as_pytest_marks(
    collector: Module | Class,
    name: str,
    obj: object,
    timeout: tuple[float, TimeUnit] | None,
    expect_fail: bool,
    expect_error: Iterable[type[BaseException]],
    skip: bool,
    stage: int,
    options: list[
        tuple[str, Sequence[object]] | tuple[Sequence[str], Sequence[Sequence[object]]]
    ]
    | None = None,
) -> object:
    if getattr(obj, "__test__", False):
        return obj  # object already unwrapped for pytest, skip it

    markers: list[Mark] = []

    # Replace @cocotb.parametrize(...) decorator with equivalent @pytest.mark.parametrize(...) markers
    # @cocotb.parametrize(x=[1, 2], y=[3, 4])
    # vvv
    # @pytest.parametrize("x", [1, 2])
    # @pytest.parametrize("y", [3, 4])
    for names, values in options or ():
        if isinstance(names, str):
            markers.append(mark.parametrize(names, values).mark)
        else:
            markers.append(mark.parametrize(",".join(names), values).mark)

    if stage:
        # Supported by external plugin: pytest-order
        markers.append(mark.order(stage).mark)

    if skip:
        markers.append(mark.skip().mark)

    if expect_fail or expect_error:
        markers.append(
            mark.xfail(
                raises=tuple(expect_error) if expect_error else None,
                strict=True,
            ).mark
        )

    if timeout:
        markers.append(mark.cocotb_timeout(duration=timeout[0], unit=timeout[1]).mark)

    markers.append(mark.cocotb_test().mark)
    markers.extend(getattr(obj, "pytestmark", ()))

    # Add pytest marks to object
    setattr(obj, "pytestmark", markers)

    # __test__ will tell pytest to treat this object as test item
    setattr(obj, "__test__", True)

    # This is needed by pytest code inspection mechanism
    setattr(collector.obj, name, obj)

    return obj
