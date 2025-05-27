# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from ._abstract_array import AbstractArray
from ._array import Array
from ._logic import Logic
from ._logic_array import LogicArray
from ._range import Range

# isort: split
# These are imports for doctests in the submodules. Since we fix up the `__module__`
# attribute, `--doctest-modules` thinks this is the module the types were defined in
# and will evaluate this module first before running tests.
from typing import Tuple  # noqa: F401

__all__ = ("AbstractArray", "Array", "Logic", "LogicArray", "Range")

# Set __module__ on re-exports
for name in __all__:
    obj = globals()[name]
    obj.__module__ = __name__
