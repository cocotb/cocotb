# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys

__all__ = ("StrEnum",)

if sys.version_info >= (3, 11):
    from enum import StrEnum

else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Backport of StrEnum from Python 3.11."""
