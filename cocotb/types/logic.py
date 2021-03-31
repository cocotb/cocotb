# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from cocotb._py_compat import cache


""" DESIGN NOTES

__singleton_cache__
    Used to ensure there is only ever one instance of a particular value.
    This is a memory optimization: there will only ever be 4 objects allocated;
    and also a speed optimization: value equality can be identity equality (as inherited from the `object` base class).

operator `isinstance(other, type(self)`
    Allows operation between a `Bit` and a `Logic` to return a `Logic`.

strict type equality
    To use `Logic` or `Bit` in hashable collections we need to define `__hash__` and `__eq__` such that
    "Hashable objects which compare equal must have the same hash value."
    (retrieved from https://hynek.me/articles/hashes-and-equality/ on 2021-03-20).
    The best way to achieve this is to make `Logic` and `Bit` never equal, like `tuple` and `list`.
    If we instead made them equal in hash and value, they would be substitutable; which we don't want.

@cache
    Shows extreme performance improvements,
    even faster than precomputing the results and storing them in the type.
    Everything can be cached since there are a (hopefully) limited number of valid values in all subclasses.
"""


class Logic:
    r"""
    Model of a 4-value (``0``, ``1``, ``X``, ``Z``) datatype commonly seen in HDLs.

    This is modeled after (System)Verilog's 4-value ``logic`` type.
    VHDL's 9-value ``std_ulogic`` type maps to this type by treating weak values as full strength values
    and treating "uninitialized" (``U``) and "don't care" (``-``) as "unknown" (``X``).

    :class:`Logic` can be converted from :class:`int`, :class:`str`, :class:`bool`, and :class:`~cocotb.types.Bit` using the ``Logic(value)`` syntax.
    The list of acceptable values includes ``0``, ``1``, ``True``, ``False``, ``'0'``, ``'1'``, ``'X'``, and ``'Z'``.
    For a comprehensive list of values that can be converted into :class:`Logic` see :file:`tests/pytest/test_logic.py`.

    :class:`Logic` can be converted to :class:`int`, :class:`str`, :class:`bool` using the appropriate constructor syntax.
    For example, ``int(Logic(0)) == 0``, ``bool(Logic(1)) is True``, and ``str(Logic('X')) == 'X'``.
    The :class:`int` and :class:`bool` conversions will raise :exc:`ValueError` if the value is not ``0`` or ``1``.

    The default value of ``Logic()`` is ``Logic('X')``.

    :class:`Logic` values are hashable and can be placed in :class:`set`\ s and used as keys in :class:`dict`\ s.

    :class:`Logic` supports the common logic operations ``&``, ``|``, ``^``, and ``~``.

    .. code-block:: py3

        def full_adder(a: Logic, b: Logic, c_in: Logic) -> (Logic, Logic):
            res = a ^ b ^ c_in
            c_out = (a & b) | (b & c_in) | (a & c_in)
            return res, c_out
    """

    __singleton_cache__ = {}

    _repr_map = {
        # 0 and weak 0
        False: 0,
        0: 0,
        "0": 0,
        "L": 0,
        "l": 0,
        # 1 and weak 1
        True: 1,
        1: 1,
        "1": 1,
        "H": 1,
        "h": 1,
        # unknown, unassigned, and weak unknown
        None: 2,
        "X": 2,
        "x": 2,
        "U": 2,
        "u": 2,
        "W": 2,
        "w": 2,
        "-": 2,
        # high impedance
        "Z": 3,
        "z": 3,
    }

    @cache
    def __new__(cls, value=None):
        # convert to internal representation
        try:
            _repr = cls._repr_map[value]
        except KeyError:
            raise ValueError(
                "{!r} is not convertible to a {}".format(value, cls.__qualname__)
            ) from None
        # ensure only one object is made per representation
        if _repr not in cls.__singleton_cache__:
            obj = super().__new__(cls)
            obj._repr = _repr
            cls.__singleton_cache__[_repr] = obj
        return cls.__singleton_cache__[_repr]

    @cache
    def __and__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(
            (
                ("0", "0", "0", "0"),
                ("0", "1", "X", "X"),
                ("0", "X", "X", "X"),
                ("0", "X", "X", "X"),
            )[self._repr][other._repr]
        )

    def __rand__(self, other):
        return self & other

    @cache
    def __or__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(
            (
                ("0", "1", "X", "X"),
                ("1", "1", "1", "1"),
                ("X", "1", "X", "X"),
                ("X", "1", "X", "X"),
            )[self._repr][other._repr]
        )

    def __ror__(self, other):
        return self | other

    @cache
    def __xor__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(
            (
                ("0", "1", "X", "X"),
                ("1", "0", "X", "X"),
                ("X", "X", "X", "X"),
                ("X", "X", "X", "X"),
            )[self._repr][other._repr]
        )

    def __rxor__(self, other):
        return self ^ other

    @cache
    def __invert__(self):
        return type(self)(("1", "0", "X", "X")[self._repr])

    @cache
    def __repr__(self):
        return "{}({!r})".format(type(self).__name__, str(self))

    @cache
    def __str__(self):
        return ("0", "1", "X", "Z")[self._repr]

    @cache
    def __bool__(self):
        if self._repr < 2:
            return bool(self._repr)
        raise ValueError(
            f"Cannot convert {self!r} to bool"
        )

    @cache
    def __int__(self):
        if self._repr < 2:
            return self._repr
        raise ValueError(
            f"Cannot convert {self!r} to int"
        )


class Bit(Logic):
    r"""
    Model of a 2-value (``0``, ``1``) datatype commonly seen in HDLs.

    This is modeled after (System)Verilog's 2-value ``bit`` type.
    VHDL's ``bit`` type maps to this type perfectly.

    :class:`Bit` can be converted from :class:`int`, :class:`str`, :class:`bool`, and :class:`~cocotb.types.Logic` using the ``Bit(value)`` syntax.
    The list of acceptable values includes ``0``, ``1``, ``True``, ``False``, ``'0'``, ``'1'``.
    For a comprehensive list of values that can be converted into :class:`Bit` see :file:`tests/pytest/test_logic.py`.

    :class:`Bit` can be converted to :class:`int`, :class:`str`, :class:`bool` using the appropriate constructor syntax.
    For example, ``int(Bit(0)) == 0``, ``bool(Bit(1)) is True``, and ``str(Bit('1')) == '1'``.

    The default value of ``Bit()`` is ``Bit('0')``.

    :class:`Bit` values are hashable and can be placed in :class:`set`\ s and used as keys in :class:`dict`\ s.

    :class:`Bit` supports the common logic operations ``&``, ``|``, ``^``, and ``~``.

    .. code-block:: py3

        def mux(a: Bit, b: Bit, s: Bit) -> Bit
            return (a & ~s) | (b & s)
    """

    # must create a separate cache for Bit
    __singleton_cache__ = {}

    _repr_map = {
        # 0
        None: 0,
        False: 0,
        0: 0,
        "0": 0,
        # 1
        True: 1,
        1: 1,
        "1": 1,
    }


Logic._repr_map.update(
    {
        Logic("0"): 0,
        Logic("1"): 1,
        Logic("X"): 2,
        Logic("Z"): 3,
        Bit("0"): 0,
        Bit("1"): 1,
    }
)

Bit._repr_map.update({Logic("0"): 0, Logic("1"): 1, Bit("0"): 0, Bit("1"): 1})
