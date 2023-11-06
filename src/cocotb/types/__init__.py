# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import typing

from .array import Array  # noqa: F401
from .logic import Bit, Logic  # noqa: F401
from .logic_array import LogicArray  # noqa: F401
from .range import Range  # noqa: F401


def concat(a: typing.Any, b: typing.Any) -> typing.Any:
    """
    Create a new array that is the concatenation of one array with another.

    Uses the :meth:`__concat__` or :meth:`__rconcat__` special methods to dispatch to a particular implementation,
    exactly like other binary operations in Python.

    Raises:
        TypeError: when the arguments do not support concatenation in the given order.
    """
    MISSING = object()
    type_a = type(a)
    type_b = type(b)
    a_concat = getattr(type_a, "__concat__", MISSING)
    a_rconcat = getattr(type_a, "__rconcat__", MISSING)
    b_rconcat = getattr(type_b, "__rconcat__", MISSING)

    if type_a is not type_b and issubclass(type_b, type_a) and a_rconcat != b_rconcat:
        # 'b' is a subclass of 'a' with a more specific implementation of 'concat(a, b)'
        call_order = [(b, b_rconcat, a), (a, a_concat, b)]
    elif type_a is not type_b:
        # normal call order
        call_order = [(a, a_concat, b), (b, b_rconcat, a)]
    else:
        # types are the same, we expect implementation of 'concat(a, b)' to be in 'a.__concat__'
        call_order = [(a, a_concat, b)]

    for lhs, method, rhs in call_order:
        if method is MISSING:
            continue
        res = method(lhs, rhs)
        if res is not NotImplemented:
            return res

    raise TypeError(
        "cannot concatenate {!r} with {!r}".format(
            type_a.__qualname__, type_b.__qualname__
        )
    )
