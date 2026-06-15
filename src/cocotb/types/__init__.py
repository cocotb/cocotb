# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from ._abstract_array import AbstractArray, AbstractMutableArray
from ._array import Array
from ._indexing import IndexingChangedWarning
from ._logic import Bit, Logic
from ._logic_array import LogicArray
from ._range import Range
from ._resolve import get_default_resolve_method, set_default_resolve_method

__all__ = (
    "AbstractArray",
    "AbstractMutableArray",
    "Array",
    "Bit",
    "IndexingChangedWarning",
    "Logic",
    "LogicArray",
    "Range",
    "get_default_resolve_method",
    "set_default_resolve_method",
)

# Set __module__ on re-exports
for name in __all__:
    obj = globals()[name]
    obj.__module__ = __name__
