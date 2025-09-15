# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from typing import Literal

if sys.version_info >= (3, 10):
    from typing import TypeAlias

RoundMode: TypeAlias = Literal["error", "round", "ceil", "floor"]
TimeUnit: TypeAlias = Literal["step", "fs", "ps", "ns", "us", "ms", "sec"]
