# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import typing
from functools import lru_cache

LogicT = typing.TypeVar("LogicT", bound="Logic")
LogicLiteralT = typing.Union[str, int, bool]
LogicConstructibleT = typing.Union[LogicLiteralT, "Logic"]


_0 = 0
_1 = 1
_X = 2
_Z = 3

_literal_repr: typing.Dict[LogicLiteralT, int] = {
    # 0 and weak 0
    False: _0,
    0: _0,
    "0": _0,
    "L": _0,
    "l": _0,
    # 1 and weak 1
    True: _1,
    1: _1,
    "1": _1,
    "H": _1,
    "h": _1,
    # unknown, unassigned, and weak unknown
    "X": _X,
    "x": _X,
    "U": _X,
    "u": _X,
    "W": _X,
    "w": _X,
    "-": _X,
    # high impedance
    "Z": _Z,
    "z": _Z,
}


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

        >>> def full_adder(a: Logic, b: Logic, carry: Logic) -> typing.Tuple[Logic, Logic]:
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
    _repr: int

    _default = _X
    _valid = {_X, _0, _1, _Z}

    @classmethod
    @lru_cache(maxsize=None)
    def _make(cls: typing.Type[LogicT], _repr: int) -> LogicT:
        """enforce singleton"""
        self = object.__new__(cls)
        self._repr = _repr
        return typing.cast(LogicT, self)

    def __new__(
        cls: typing.Type[LogicT],
        value: typing.Optional[LogicConstructibleT] = None,
    ) -> LogicT:
        if isinstance(value, Logic):
            # convert Logic
            _repr = value._repr
        elif value is None:
            _repr = cls._default
        else:
            # convert literal
            try:
                _repr = _literal_repr[value]
            except KeyError:
                raise ValueError(
                    "{!r} is not convertible to a {}".format(value, cls.__qualname__)
                ) from None
        if _repr not in cls._valid:
            raise ValueError("{!r} is not a valid {}".format(value, cls.__qualname__))
        obj = cls._make(_repr)
        return obj

    if not typing.TYPE_CHECKING:  # pragma: no cover
        # mypy currently does not support lru_cache on __new__
        __new__ = lru_cache(maxsize=None)(__new__)

    def __and__(self: LogicT, other: LogicT) -> LogicT:
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

    def __rand__(self: LogicT, other: LogicT) -> LogicT:
        return self & other

    def __or__(self: LogicT, other: LogicT) -> LogicT:
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

    def __ror__(self: LogicT, other: LogicT) -> LogicT:
        return self | other

    def __xor__(self: LogicT, other: LogicT) -> LogicT:
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

    def __rxor__(self: LogicT, other: LogicT) -> LogicT:
        return self ^ other

    def __invert__(self: LogicT) -> LogicT:
        return type(self)(("1", "0", "X", "X")[self._repr])

    def __eq__(self, other: object) -> bool:
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
        if self._repr in {_0, _1}:
            return bool(self._repr)
        raise ValueError(f"Cannot convert {self!r} to bool")

    def __int__(self) -> int:
        if self._repr in {_0, _1}:
            return int(self._repr)
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

    _default = _0
    _valid = {_0, _1}
