# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test ``@cocotb.*`` decorators with pytest used as regression manager for cocotb tests."""

from __future__ import annotations

import cocotb
from cocotb.triggers import FallingEdge, SimTimeoutError


@cocotb.test
async def test_default_1(dut) -> None:
    """Test default arguments from @cocotb.test decorator."""


@cocotb.test()
async def test_default_2(dut) -> None:
    """Test default arguments from @cocotb.test decorator."""


@cocotb.test(skip=True)
async def test_skip_true(dut) -> None:
    """Test skip from @cocotb.test decorator."""
    raise RuntimeError("skipped error")


@cocotb.test(skip=False)
async def test_skip_false(dut) -> None:
    """Test skip from @cocotb.test decorator."""


@cocotb.test(timeout_time=100, timeout_unit="ns", expect_error=SimTimeoutError)
async def test_timeout(dut) -> None:
    """Test timeout from @cocotb.test decorator."""
    for _ in range(100):
        await FallingEdge(dut.clk)


@cocotb.test(expect_fail=True)
async def test_expect_fail_true(dut) -> None:
    """Test expect fail from @cocotb.test decorator."""
    raise RuntimeError("expecting any error")


@cocotb.test(expect_fail=False)
async def test_expect_fail_false(dut) -> None:
    """Test expect fail from @cocotb.test decorator."""


@cocotb.test(expect_error=None)
async def test_expect_error_none(dut) -> None:
    """Test expect error from @cocotb.test decorator."""


@cocotb.test(expect_error=RuntimeError)
async def test_expect_error_1(dut) -> None:
    """Test expect error from @cocotb.test decorator."""
    raise RuntimeError("expecting runtime error")


@cocotb.test(expect_error=(RuntimeError, ValueError))
async def test_expect_error_2(dut) -> None:
    """Test expect error from @cocotb.test decorator."""
    raise ValueError("expecting value error")


@cocotb.xfail()
async def test_xfail_default(dut) -> None:
    """Test @cocotb.xfail decorator."""
    raise RuntimeError("expecting any error")


@cocotb.xfail(raises=None)
async def test_xfail_raises_none(dut) -> None:
    """Test @cocotb.xfail decorator."""
    raise RuntimeError("expecting any error")


@cocotb.xfail(raises=RuntimeError)
async def test_xfail_raises_1(dut) -> None:
    """Test @cocotb.xfail decorator."""
    raise RuntimeError("expecting runtime error")


@cocotb.xfail(raises=(RuntimeError, ValueError))
async def test_xfail_raises_2(dut) -> None:
    """Test @cocotb.xfail decorator."""
    raise ValueError("expecting value error")


@cocotb.xfail(condition=False)
async def test_xfail_condition_false(dut) -> None:
    """Test @cocotb.xfail decorator."""


@cocotb.xfail(condition=True)
async def test_xfail_condition_true(dut) -> None:
    """Test @cocotb.xfail decorator."""
    raise RuntimeError("expecting any error")


@cocotb.xfail(reason="not yet supported")
async def test_xfail_reason_message(dut) -> None:
    """Test @cocotb.xfail decorator."""
    raise RuntimeError("expecting any error")


@cocotb.skipif(True)
async def test_skipif_true(dut) -> None:
    """Test @cocotb.skipif decorator."""
    raise RuntimeError("skipped error")


@cocotb.skipif(False)
async def test_skipif_false(dut) -> None:
    """Test @cocotb.skipif decorator."""


@cocotb.parametrize()
async def test_parametrize_empty(dut) -> None:
    """Test @cocotb.parametrize decorator."""


@cocotb.parametrize(x=[1, 2], y=[3, 4, 5])
async def test_parametrize_matrix(dut, x: int, y: int) -> None:
    """Test @cocotb.parametrize decorator."""
    assert x in (1, 2)
    assert y in (3, 4, 5)


@cocotb.parametrize((("a", "b"), [(1, 2), (3, 4)]))
async def test_parametrize_series_1(dut, a: int, b: int) -> None:
    """Test @cocotb.parametrize decorator."""
    assert (a == 1 and b == 2) or (a == 3 and b == 4)


@cocotb.parametrize(
    (
        ("x", "y"),
        ((1, 2), (3, 4)),
    ),
    (
        "z",
        (5, 6),
    ),
)
async def test_parametrize_series_2(dut, x: int, y: int, z: int) -> None:
    """Test @cocotb.parametrize decorator."""
    assert x in (1, 3)
    assert y in (2, 4)
    assert z in (5, 6)


class TestClass:
    @cocotb.test
    async def test_simple(dut) -> None:
        """Test @cocotb.test under class."""

    @cocotb.parametrize(x=(1, 2), y=(3, 4))
    async def test_parametrize_matrix(dut, x: int, y: int) -> None:
        """Test @cocotb.parametrize under class."""
        assert x in (1, 2)
        assert y in (3, 4)
