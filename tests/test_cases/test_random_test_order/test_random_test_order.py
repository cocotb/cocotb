# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb

# Track which test gets ran during the simulation.
count = 0


# Try this a parametrized version of a test.
@cocotb.test(stage=0)
@cocotb.parametrize(index=[0, 1, 2])
async def test_a0(dut: object, index: int) -> None:
    """Run a test."""
    global count
    count += 1
    if index == 0:
        assert count == 3
    elif index == 1:
        assert count == 2
    elif index == 2:
        assert count == 5


@cocotb.test(stage=0)
async def test_b0(dut: object) -> None:
    """Run a test."""
    global count
    count += 1
    assert count == 1


@cocotb.test(stage=0)
async def test_c0(dut: object) -> None:
    """Run a test."""
    global count
    count += 1
    assert count == 4


# Try with a test in a different stage.
@cocotb.test(stage=1)
async def test_a1(dut: object) -> None:
    """Run a test."""
    global count
    count += 1
    # Verify this test is always last.
    assert count == 6
