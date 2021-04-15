# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from .logic import Logic, Bit  # noqa: F401
from .range import Range  # noqa: F401
from .array import Array  # noqa: F401


def concat(a: Array, b: Array) -> Array:
    """
    Create a new array that is the concatenation of one array with another.

    Uses the :meth:`__concat__` or :meth:`__rconcat__` special methods to dispatch to a particular implementation,
    exactly like other binary operations in Python.

    Raises:
        TypeError: when the arguments do not support concatenation in the given order.
    """
    if hasattr(a, '__concat__'):
        res = a.__concat__(b)
        if res is not NotImplemented:
            return res
    if hasattr(b, '__rconcat__'):
        res = b.__rconcat__(a)
        if res is not NotImplemented:
            return res
    raise TypeError(
        "cannot concatenate {!r} with {!r}".format(
            a.__class__.__qualname__, b.__class__.__qualname__
        )
    )
