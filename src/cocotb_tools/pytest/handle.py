# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Facilities to mock cocotb sim handle when collecting test items
from the main pytest parent process, outside of HDL simulation environment.

This is need to avoid raising an :py:exc:`AttributeError` or :py:exc:`KeyError` exception
when accessing :py:data:`cocotb.top` global variable during pytest collection phase.
"""

from __future__ import annotations


class MockSimHandle:
    """Mocking :py:class:`cocotb.handle.SimHandleBase`."""

    def __getitem__(self, key: str) -> MockSimHandle:
        """Mock nested access to item ``obj[a][b][c]``."""
        return MockSimHandle()

    def __getattr__(self, key: str) -> MockSimHandle:
        """Mock nested access to attribute ``obj.a.b.c``."""
        return MockSimHandle()

    def __len__(self) -> int:
        """Mock collections."""
        return 0
