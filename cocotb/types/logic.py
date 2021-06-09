# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from typing import Any, Optional, Dict
from typing import Tuple  # noqa: F401
from functools import lru_cache


class _StaticOnlyProp:

    def __init__(self, fget):
        self.fget = fget

    def __set_name__(self, cls, name):
        self.__cls = cls

    def __get__(self, instance, cls):
        if cls is not self.__cls or instance is not None:
            raise AttributeError
        return self.fget()


class Logic:
    r"""
    Model of a 4-value (``0``, ``1``, ``X``, ``Z``) datatype commonly seen in HDLs.

    .. currentmodule:: cocotb.types

    This is modeled after (System)Verilog's 4-value ``logic`` type.
    VHDL's 9-value ``std_ulogic`` type maps to this type by treating weak values as full strength values
    and treating "uninitialized" (``U``) and "don't care" (``-``) as "unknown" (``X``).

    :class:`Logic` can be converted to and from :class:`int`, :class:`str`, :class:`bool`, and :class:`Bit`
    by using the appropriate constructor syntax.
    The list of values convertable to :class:`Logic` includes
    ``0``, ``1``, ``True``, ``False``, ``"0"``, ``"1"``, ``"X"``, ``"Z"``, ``Bit('0')``, and ``Bit('1')``.
    For a comprehensive list of values that can be converted into :class:`Logic` see :file:`tests/pytest/test_logic.py`.

    .. code-block:: python3

        >>> Logic("X")
        Logic('X')
        >>> Logic(True)
        Logic('1')
        >>> Logic(1)
        Logic('1')
        >>> Logic(Bit(0))
        Logic('0')

        >>> Logic()  # default value
        Logic('X')

        >>> str(Logic("Z"))
        'Z'
        >>> bool(Logic(0))
        False
        >>> int(Logic(1))
        1
        >>> Bit(Logic("1"))
        Bit('1')

    .. note::

        The :class:`int` and :class:`bool` conversions will raise :exc:`ValueError` if the value is not ``0`` or ``1``.

    :class:`Logic` values are immutable and therefore hashable and can be placed in :class:`set`\ s and used as keys in :class:`dict`\ s.

    :class:`Logic` supports the common logic operations ``&``, ``|``, ``^``, and ``~``.

    .. code-block:: python3

        >>> def full_adder(a: Logic, b: Logic, carry: Logic) -> Tuple[Logic, Logic]:
        ...     res = a ^ b ^ carry
        ...     carry_out = (a & b) | (b & carry) | (a & carry)
        ...     return res, carry_out

        >>> full_adder(a=Logic('0'), b=Logic('1'), carry=Logic('1'))
        (Logic('0'), Logic('1'))

    Args:
        value: value to construct into a :class:`Logic`.

    Raises:
        ValueError: if the value cannot be constructed into a :class:`Logic`.
    """
    __slots__ = ("_repr",)

    __singleton_cache__: Dict[int, "Logic"] = {}

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

    @_StaticOnlyProp
    def _0():
        return Logic("0")

    @_StaticOnlyProp
    def _1():
        return Logic("1")

    @_StaticOnlyProp
    def X():
        return Logic("X")

    @_StaticOnlyProp
    def Z():
        return Logic("Z")

    @lru_cache(maxsize=None)
    def __new__(cls, value: Optional[Any] = None) -> "Logic":
        # convert to internal representation
        try:
            _repr = cls._repr_map[value]
        except KeyError:
            raise ValueError(
                "{!r} is not convertible to a {}".format(value, cls.__qualname__)
            ) from None
        obj = cls.__singleton_cache__.get(_repr, None)
        if obj is None:
            obj = super().__new__(cls)
            obj._repr = _repr
            cls.__singleton_cache__[_repr] = obj
        return obj

    def __and__(self, other: "Logic") -> "Logic":
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

    def __rand__(self, other: "Logic") -> "Logic":
        return self & other

    def __or__(self, other: "Logic") -> "Logic":
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

    def __ror__(self, other: "Logic") -> "Logic":
        return self | other

    def __xor__(self, other: "Logic") -> "Logic":
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

    def __rxor__(self, other: "Logic") -> "Logic":
        return self ^ other

    def __invert__(self) -> "Logic":
        return type(self)(("1", "0", "X", "X")[self._repr])

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._repr == other._repr

    def __hash__(self) -> int:
        return self._repr

    def __repr__(self) -> str:
        return "{}({!r})".format(type(self).__qualname__, str(self))

    def __str__(self) -> str:
        return ("0", "1", "X", "Z")[self._repr]

    def __bool__(self) -> bool:
        if self._repr < 2:
            return bool(self._repr)
        raise ValueError(f"Cannot convert {self!r} to bool")

    def __int__(self) -> int:
        if self._repr < 2:
            return self._repr
        raise ValueError(f"Cannot convert {self!r} to int")


class Bit(Logic):
    r"""
    Model of a 2-value (``0``, ``1``) datatype commonly seen in HDLs.

    .. currentmodule:: cocotb.types

    This is modeled after (System)Verilog's 2-value ``bit`` type.
    VHDL's ``bit`` type maps to this type perfectly.

    :class:`Bit` is a proper subtype of :class:`Logic`, meaning a use of :class:`Logic` can be substituted with a :class:`Bit`.
    Some behavior may surprise you if you do not expect it.

    .. code-block:: python3

        >>> Bit(0) == Logic(0)
        True
        >>> Bit(0) in {Logic(0)}
        True

    :class:`Bit` can be converted to and from :class:`int`, :class:`str`, :class:`bool`, and :class:`Logic`
    by using the appropriate constructor syntax.
    The list of values convertable to :class:`Bit` includes
    ``0``, ``1``, ``True``, ``False``, ``"0"``, ``"1"``, ``Logic('0')``, and ``Logic('1')``.
    For a comprehensive list of values that can be converted into :class:`Bit` see :file:`tests/pytest/test_logic.py`.

    .. code-block:: python3

        >>> Bit("0")
        Bit('0')
        >>> Bit(True)
        Bit('1')
        >>> Bit(1)
        Bit('1')
        >>> Bit(Logic(0))
        Bit('0')

        >>> Bit()  # default value
        Bit('0')

        >>> str(Bit("0"))
        '0'
        >>> bool(Bit(False))
        False
        >>> int(Bit(1))
        1
        >>> Logic(Bit("1"))
        Logic('1')

    :class:`Bit` values are hashable and can be placed in :class:`set`\ s and used as keys in :class:`dict`\ s.

    :class:`Bit` supports the common logic operations ``&``, ``|``, ``^``, and ``~``.

    .. code-block:: py3

        >>> def mux(a: Bit, b: Bit, s: Bit) -> Bit:
        ...     return (a & ~s) | (b & s)

        >>> a = Bit(0)
        >>> b = Bit(1)
        >>> sel = Bit(1)  # choose second argument
        >>> mux(a, b, sel)
        Bit('1')

    Args:
        value: value to construct into a :class:`Bit`.

    Raises:
        ValueError: if the value cannot be constructed into a :class:`Bit`.
    """
    __slots__ = ()

    __singleton_cache__: Dict[int, "Bit"] = {}

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

    @_StaticOnlyProp
    def _0():
        return Bit("0")

    @_StaticOnlyProp
    def _1():
        return Bit("1")


Logic._repr_map.update(
    {
        Logic("0"): 0,
        Logic("1"): 1,
        Logic("X"): 2,
        Logic("Z"): 3,
    }
)

Bit._repr_map.update({Bit("0"): 0, Bit("1"): 1})
