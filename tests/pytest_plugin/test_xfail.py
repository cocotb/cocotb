# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test ``@pytest.mark.xfail`` for cocotb tests."""

from __future__ import annotations

import pytest

import cocotb


@pytest.mark.xfail
async def test_any(dut) -> None:
    """Test ``@pytest.mark.xfail`` with any raise."""
    raise ValueError("expecting any error")


@cocotb.xfail(raises=RuntimeError)
async def test_raises_1(dut) -> None:
    """Test ``@pytest.mark.xfail`` with raises."""
    raise RuntimeError("expecting runtime error")


@cocotb.xfail(raises=(RuntimeError, ValueError))
async def test_raises_2(dut) -> None:
    """Test ``@pytest.mark.xfail`` with raises."""
    raise ValueError("expecting value error")


@pytest.mark.xfail(raises=RuntimeError, strict=True)
async def test_raises_strict(dut) -> None:
    """Test ``@pytest.mark.xfail`` with raises and strict."""
    raise RuntimeError("expecting runtime error")


@pytest.mark.xfail(strict=True)
async def test_any_strict(dut) -> None:
    """Test ``@pytest.mark.xfail`` with any raise."""
    raise ValueError("expecting any error")
