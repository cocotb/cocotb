# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import sys

if sys.version_info >= (3, 10):
    from typing import (
        Literal,  # noqa: F401  # This type is used in type strings in this module
        TypeAlias,
    )

TimeUnitWithoutStep: "TypeAlias" = 'Literal["fs", "ps", "ns", "us", "ms", "sec"]'
TimeUnit: "TypeAlias" = 'Literal["step"] | TimeUnitWithoutStep'
