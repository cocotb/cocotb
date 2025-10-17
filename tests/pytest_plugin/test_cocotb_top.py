# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :py:data:`cocotb.top` with pytest decorators."""

from __future__ import annotations

import pytest

import cocotb


@pytest.mark.skipif(cocotb.top.INT_PARAM.value == 0, reason="")
async def test_eq(dut) -> None:
    """Test `cocotb.top.ATTR == X`."""


@pytest.mark.skipif(cocotb.top.INT_PARAM.value != 0, reason="")
async def test_nq(dut) -> None:
    """Test `cocotb.top.ATTR != X`."""


@pytest.mark.skipif(int(cocotb.top.INT_PARAM.value) < 0, reason="")
async def test_lt(dut) -> None:
    """Test `cocotb.top.ATTR < X`."""


@pytest.mark.skipif(int(cocotb.top.INT_PARAM.value) <= 0, reason="")
async def test_le(dut) -> None:
    """Test `cocotb.top.ATTR <= X`."""


@pytest.mark.skipif(int(cocotb.top.INT_PARAM.value) > 0, reason="")
async def test_gt(dut) -> None:
    """Test `cocotb.top.ATTR > X`."""


@pytest.mark.skipif(int(cocotb.top.INT_PARAM.value) >= 0, reason="")
async def test_ge(dut) -> None:
    """Test `cocotb.top.ATTR >= X`."""


@pytest.mark.skipif(cocotb.top.INT_PARAM.value, reason="")
async def test_value(dut) -> None:
    """Test `cocotb.top.ATTR`."""
