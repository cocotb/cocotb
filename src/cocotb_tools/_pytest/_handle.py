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
        return self

    def __getattr__(self, key: str) -> MockSimHandle:
        """Mock nested access to attribute ``obj.a.b.c``."""
        return self

    def __call__(self, *args: object, **kwargs: object) -> MockSimHandle:
        """Mock calling methods."""
        return self

    def __int__(self) -> int:
        """Mock casting to integer."""
        return 0

    def __eq__(self, other: object) -> bool:
        """Mock ``==``."""
        return False

    def __nq__(self, other: object) -> bool:
        """Mock ``!=``."""
        return False

    def __le__(self, other: object) -> bool:
        """Mock ``<=``."""
        return False

    def __lt__(self, other: object) -> bool:
        """Mock ``<``."""
        return False

    def __ge__(self, other: object) -> bool:
        """Mock ``>=``."""
        return False

    def __gt__(self, other: object) -> bool:
        """Mock ``>``."""
        return False

    def __len__(self) -> int:
        """Mock collections."""
        return 0
