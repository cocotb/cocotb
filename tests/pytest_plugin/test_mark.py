# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :class:`cocotb_tools._pytest.mark` module."""

from __future__ import annotations

from pytest import MarkDecorator

from cocotb_tools._pytest import mark


def test_pytest_plugin_mark_cocotb() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb` marker."""
    marker: MarkDecorator = mark.cocotb()
    assert len(marker.args) == 0
    assert len(marker.kwargs) == 0
    assert marker.__doc__


def test_pytest_plugin_mark_cocotb_timeout() -> None:
    """Test signature of :deco:`cocotb_tools.pytest.mark.cocotb_timeout` marker."""
    marker: MarkDecorator = mark.cocotb_timeout(100, "ns")
    assert len(marker.args) == 0
    assert len(marker.kwargs) == 2
    assert marker.kwargs["duration"] == 100
    assert marker.kwargs["unit"] == "ns"
    assert marker.__doc__
