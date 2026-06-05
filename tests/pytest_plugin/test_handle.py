# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test the :class:`cocotb_tools.pytest._handle.MockSimHandle` class that is mocking the :data:`cocotb.top` handle."""

from __future__ import annotations

from typing import Any

from cocotb_tools.pytest._handle import MockSimHandle


def test_handle_sim_mock() -> None:
    """Test the :class:`cocotb_tools.pytest._handle.MockSimHandle` class."""
    handle = MockSimHandle()

    assert handle is not None
    assert handle["A"] is handle
    assert handle["A"]["B"] is handle
    assert handle.a is handle
    assert handle.a.b.c is handle
    assert handle() is handle
    assert handle(1, "a", True) is handle
    assert handle(a=1, b="c", d=True) is handle
    assert handle(2, "b", False, c=3) is handle
    assert len(handle) == 0
    assert int(handle) == 0
    assert str(handle)
    assert repr(handle)

    value: Any

    for value in (-1, 0, 1, False, True, "a", None, [], ()):
        assert not handle == value
        assert not handle != value
        assert not handle > value
        assert not handle >= value
        assert not handle < value
        assert not handle <= value
