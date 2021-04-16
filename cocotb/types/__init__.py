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
    a_concat = getattr(a.__class__, "__concat__", None)
    a_rconcat = getattr(a.__class__, "__rconcat__", None)
    b_rconcat = getattr(b.__class__, "__rconcat__", None)

    if isinstance(b, a.__class__) and a_rconcat != b_rconcat:
        # 'b' is a subclass of 'a' with a more specific implementation of 'concat(a, b)'
        call_order = ((b, b_rconcat, a), (a, a_concat, b))
    elif a.__class__ != b.__class__:
        # normal call order
        call_order = ((a, a_concat, b), (b, b_rconcat, a))
    else:
        # types are the same, we expect implementation of 'concat(a, b)' to be in 'a.__concat__'
        call_order = ((a, a_concat, b),)

    for lhs, method, rhs in call_order:
        if method is None:
            continue
        res = method(lhs, rhs)
        if res is not NotImplemented:
            return res

    raise TypeError(
        "cannot concatenate {!r} with {!r}".format(
            a.__class__.__qualname__, b.__class__.__qualname__
        )
    )
