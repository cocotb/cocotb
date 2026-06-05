# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Provides mock cocotb simulation handles when collecting test items.

This is used in the main pytest parent process (outside the HDL simulation environment)
to avoid raising an :exc:`AttributeError` or :exc:`KeyError` when accessing the
:data:`cocotb.top` global variable during the pytest collection phase.
"""

from __future__ import annotations


class MockSimHandle:
    """A mock class representing :class:`cocotb.handle.SimHandleBase`.

    This class allows arbitrary attribute and item access, returning itself
    for nested lookups and default values for comparisons and casts.
    """

    def __getitem__(self, key: str) -> MockSimHandle:
        """Mock nested item access."""
        return self

    def __getattr__(self, key: str) -> MockSimHandle:
        """Mock nested attribute access."""
        return self

    def __call__(self, *args: object, **kwargs: object) -> MockSimHandle:
        """Mock calling methods or objects."""
        return self

    def __int__(self) -> int:
        """Mock integer conversion, returning 0."""
        return 0

    def __eq__(self, other: object) -> bool:
        """Mock the equality comparison, returning False."""
        return False

    def __ne__(self, other: object) -> bool:
        """Mock the inequality comparison, returning False."""
        return False

    def __le__(self, other: object) -> bool:
        """Mock the less-than-or-equal comparison, returning False."""
        return False

    def __lt__(self, other: object) -> bool:
        """Mock the less-than comparison, returning False."""
        return False

    def __ge__(self, other: object) -> bool:
        """Mock the greater-than-or-equal comparison, returning False."""
        return False

    def __gt__(self, other: object) -> bool:
        """Mock the greater-than comparison, returning False."""
        return False

    def __len__(self) -> int:
        """Mock the length query, returning 0."""
        return 0
