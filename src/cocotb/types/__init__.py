# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from ._abstract_array import AbstractArray
from ._array import Array
from ._logic import Logic
from ._logic_array import RESOLVE_X, LogicArray, ResolveX
from ._range import Range

__all__ = (
    "Range",
    "Array",
    "Logic",
    "LogicArray",
    "ResolveX",
    "RESOLVE_X",
    "AbstractArray",
)

# Change module to get correct linking in Sphinx
AbstractArray.__module__ = __name__
Array.__module__ = __name__
LogicArray.__module__ = __name__
Range.__module__ = __name__
ResolveX.__module__ = __name__
