# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Backports and compatibility shims for newer python features.

These are for internal use - users should use a third party library like `six`
if they want to use these shims in their own code
"""

from __future__ import annotations

import sys

__all__ = ("StrEnum",)

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value
