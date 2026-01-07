# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test ``@pytest.mark.parametrize`` for cocotb tests."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize("x", [1, 2])
@pytest.mark.parametrize("y", [3, 4, 5])
async def test_matrix(dut, x: int, y: int) -> None:
    """Test @pytest.mark.parametrize."""
    assert x in (1, 2)
    assert y in (3, 4, 5)


@pytest.mark.parametrize("x,y", ((1, 2), (3, 4)))
@pytest.mark.parametrize("z", (5, 6))
async def test_series(dut, x: int, y: int, z: int) -> None:
    """Test @pytest.mark.parametrize."""
    assert x in (1, 3)
    assert y in (2, 4)
    assert z in (5, 6)


@pytest.mark.parametrize("z", (1, 2))
class TestParametrize:
    async def test_from_class(dut, z: int) -> None:
        """Test @pytest.mark.parametrize."""
        assert z in (1, 2)

    @pytest.mark.parametrize("x", [4, 5])
    @pytest.mark.parametrize("y", [6, 7, 8])
    async def test_matrix(dut, x: int, y: int, z: int) -> None:
        """Test @pytest.mark.parametrize."""
        assert x in (4, 5)
        assert y in (6, 7, 8)
        assert z in (1, 2)

    @pytest.mark.parametrize("x,y", ((7, 8), (9, 4)))
    async def test_series(dut, x: int, y: int, z: int) -> None:
        """Test @pytest.mark.parametrize."""
        assert x in (7, 9)
        assert y in (8, 4)
        assert z in (1, 2)
