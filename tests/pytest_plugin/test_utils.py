# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test the :mod:`cocotb_tools.pytest._utils` module."""

from __future__ import annotations

from cocotb_tools.pytest._utils import to_list


def test_utils_to_list() -> None:
    """Test the :func:`cocotb_tools.pytest._utils.to_list` function."""
    for value in (None, False, True, -1, 0, 1, "foo"):
        assert to_list(value) == [value]

    assert to_list((1, 2, 3)) == [1, 2, 3]
    assert to_list([4, 5, 6]) == [4, 5, 6]
