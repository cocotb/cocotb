# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from typing import TypeAlias

RoundMode: TypeAlias = Literal["error", "round", "ceil", "floor"]
TimeUnit: TypeAlias = Literal["step", "fs", "ps", "ns", "us", "ms", "sec"]
