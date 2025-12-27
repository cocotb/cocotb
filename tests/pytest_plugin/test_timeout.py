# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test timeout with :py:deco:`cocotb_tools.pytest.mark.cocotb_timeout` marker."""

from __future__ import annotations

import pytest

from cocotb.triggers import FallingEdge, SimTimeoutError


@pytest.mark.xfail(raises=SimTimeoutError)
@pytest.mark.cocotb_timeout(100, "ns")
async def test_timeout_with_positional_arguments(dut) -> None:
    """Test timeout with :py:deco:`cocotb_tools.pytest.mark.cocotb_timeout` marker."""
    for _ in range(100):
        await FallingEdge(dut.clk)


@pytest.mark.xfail(raises=SimTimeoutError)
@pytest.mark.cocotb_timeout(duration=40, unit="ns")
async def test_timeout_with_named_arguments(dut) -> None:
    """Test timeout with :py:deco:`cocotb_tools.pytest.mark.cocotb_timeout` marker."""
    for _ in range(100):
        await FallingEdge(dut.clk)
