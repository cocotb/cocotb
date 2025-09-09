# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from functools import lru_cache
from typing import (
    Dict,
    Union,
)

from cocotb._py_compat import Self, TypeAlias
from cocotb.types._resolve import RESOLVE_X, ResolverLiteral, get_str_resolver

LogicLiteralT: TypeAlias = Union[str, int, bool]
LogicConstructibleT: TypeAlias = Union[LogicLiteralT, "Logic"]


_U = 0
_X = 1
_0 = 2
_1 = 3
_Z = 4
_W = 5
_L = 6
_H = 7
_D = 8

_literal_repr: Dict[LogicLiteralT, int] = {
    # unassigned
    "U": _U,
    "u": _U,
    # unknown
    "X": _X,
    "x": _X,
    # 0
    0: _0,  # Also `False`
    "0": _0,
    # 1
    1: _1,  # Also `True`
    "1": _1,
    # high impedance
    "Z": _Z,
    "z": _Z,
    # weak unknown
    "W": _W,
    "w": _W,
    # weak 0
    "L": _L,
    "l": _L,
    # weak 1
    "H": _H,
    "h": _H,
    # don't care
    "-": _D,
}


class Logic:
    r"""9-state digital signal value type.

    This type is modeled after VHDL's ``std_ulogic`` type.
    It can represent the values (``U``, ``X``, ``0``, ``1``, ``Z``, ``W``, ``L``, ``H``, ``-``).
    (System)Verilog's 4-state ``logic`` type is a subset which only utilizes the ``X``, ``0``, ``1``, and ``Z`` values.

    :class:`!Logic` can be converted to and from :class:`int`, :class:`str`, :class:`bool` and :class:`Bit`.
    String literals include ``"U"``, ``"X"``, ``"0"``, ``"1"``, ``"Z"``, ``"W"``, ``"L"``, ``"H"``, ``"-"``, and their lowercase values.

    .. code-block:: pycon3

        >>> Logic("X")
        Logic('X')
        >>> Logic(True)
        Logic('1')
        >>> Logic(1)
        Logic('1')

        >>> str(Logic("Z"))
        'Z'
        >>> bool(Logic(0))
        False
        >>> int(Logic(1))
        1

    .. note::

        The :class:`int` and :class:`bool` conversions will raise :exc:`ValueError` if the value is not ``0``, ``1``, ``L``, or ``H``.

    :class:`Logic` supports the common logic operations ``&``, ``|``, ``^``, and ``~``.

    .. code-block:: pycon3

        >>> def full_adder(a: Logic, b: Logic, carry: Logic) -> Tuple[Logic, Logic]:
        ...     res = a ^ b ^ carry
        ...     carry_out = (a & b) | (b & carry) | (a & carry)
        ...     return res, carry_out

        >>> full_adder(a=Logic("0"), b=Logic("1"), carry=Logic("1"))
        (Logic('0'), Logic('1'))

    Args:
        value: value to construct into a :class:`!Logic`.

    Raises:
        ValueError: If the value if of the correct type, but cannot be constructed into a :class:`!Logic`.
        TypeError: If the value is of a type that can't be constructed into a :class:`!Logic`.
    """

    _values = {_U, _X, _0, _1, _Z, _W, _L, _H, _D}

    _repr: int

    __slots__ = ("_repr",)

    @classmethod
    @lru_cache(maxsize=None)
    def _singleton(cls, _repr: int) -> Self:
        """Return the Logic object associated with the repr, enforcing singleton."""
        self = object.__new__(cls)
        self._repr = _repr
        return self

    def __new__(
        cls,
        value: LogicConstructibleT,
    ) -> Self:
        if isinstance(value, Logic):
            _repr = value._repr
        elif isinstance(value, (str, int)):
            try:
                _repr = _literal_repr[value]
            except KeyError:
                raise ValueError(
                    f"{value!r} is not convertible to {cls.__qualname__}"
                ) from None
        else:
            raise TypeError(
                f"Expected str, bool, or int, not {type(value).__qualname__}"
            )

        if _repr not in cls._values:
            raise ValueError(f"{value!r} is not a valid {cls.__qualname__}")

        return cls._singleton(_repr)

    def __and__(self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(
            (
                # -----------------------------------------------------
                # U    X    0    1    Z    W    L    H    -       |   |
                # -----------------------------------------------------
                ("U", "U", "0", "U", "U", "U", "0", "U", "U"),  # | U |
                ("U", "X", "0", "X", "X", "X", "0", "X", "X"),  # | X |
                ("0", "0", "0", "0", "0", "0", "0", "0", "0"),  # | 0 |
                ("U", "X", "0", "1", "X", "X", "0", "1", "X"),  # | 1 |
                ("U", "X", "0", "X", "X", "X", "0", "X", "X"),  # | Z |
                ("U", "X", "0", "X", "X", "X", "0", "X", "X"),  # | W |
                ("0", "0", "0", "0", "0", "0", "0", "0", "0"),  # | L |
                ("U", "X", "0", "1", "X", "X", "0", "1", "X"),  # | H |
                ("U", "X", "0", "X", "X", "X", "0", "X", "X"),  # | - |
            )[self._repr][other._repr]
        )

    def __rand__(self, other: Self) -> Self:
        return self & other

    def __or__(self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(
            (
                # -----------------------------------------------------
                # U    X    0    1    Z    W    L    H    -       |   |
                # -----------------------------------------------------
                ("U", "U", "U", "1", "U", "U", "U", "1", "U"),  # | U |
                ("U", "X", "X", "1", "X", "X", "X", "1", "X"),  # | X |
                ("U", "X", "0", "1", "X", "X", "0", "1", "X"),  # | 0 |
                ("1", "1", "1", "1", "1", "1", "1", "1", "1"),  # | 1 |
                ("U", "X", "X", "1", "X", "X", "X", "1", "X"),  # | Z |
                ("U", "X", "X", "1", "X", "X", "X", "1", "X"),  # | W |
                ("U", "X", "0", "1", "X", "X", "0", "1", "X"),  # | L |
                ("1", "1", "1", "1", "1", "1", "1", "1", "1"),  # | H |
                ("U", "X", "X", "1", "X", "X", "X", "1", "X"),  # | - |
            )[self._repr][other._repr]
        )

    def __ror__(self, other: Self) -> Self:
        return self | other

    def __xor__(self, other: Self) -> Self:
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(
            (
                # -----------------------------------------------------
                # U    X    0    1    Z    W    L    H    -       |   |
                # -----------------------------------------------------
                ("U", "U", "U", "U", "U", "U", "U", "U", "U"),  # | U |
                ("U", "X", "X", "X", "X", "X", "X", "X", "X"),  # | X |
                ("U", "X", "0", "1", "X", "X", "0", "1", "X"),  # | 0 |
                ("U", "X", "1", "0", "X", "X", "1", "0", "X"),  # | 1 |
                ("U", "X", "X", "X", "X", "X", "X", "X", "X"),  # | Z |
                ("U", "X", "X", "X", "X", "X", "X", "X", "X"),  # | W |
                ("U", "X", "0", "1", "X", "X", "0", "1", "X"),  # | L |
                ("U", "X", "1", "0", "X", "X", "1", "0", "X"),  # | H |
                ("U", "X", "X", "X", "X", "X", "X", "X", "X"),  # | - |
            )[self._repr][other._repr]
        )

    def __rxor__(self, other: Self) -> Self:
        return self ^ other

    def __invert__(self) -> Self:
        return type(self)(("U", "X", "1", "0", "X", "X", "1", "0", "X")[self._repr])

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Logic):
            return self._repr == other._repr
        elif isinstance(other, (int, str, bool)):
            try:
                other = Logic(other)
            except ValueError:
                return False
            return self == other
        else:
            return NotImplemented

    __hash__: None  # type: ignore[assignment]

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({str(self)!r})"

    def __str__(self) -> str:
        return ("U", "X", "0", "1", "Z", "W", "L", "H", "-")[self._repr]

    if RESOLVE_X is None:

        def __bool__(self) -> bool:
            if self._repr in (_0, _L):
                return False
            elif self._repr in (_1, _H):
                return True
            raise ValueError(f"Cannot convert {self!r} to bool")

        def __int__(self) -> int:
            if self._repr in (_0, _L):
                return 0
            elif self._repr in (_1, _H):
                return 1
            raise ValueError(f"Cannot convert {self!r} to int")

    else:

        def __bool__(self) -> bool:
            return self._repr in (_1, _H)

        def __int__(self) -> int:
            s = str(self)
            s = RESOLVE_X(s)
            return int(s, 2)

    def __index__(self) -> int:
        return int(self)

    def resolve(self, resolver: ResolverLiteral) -> Self:
        """Resolve non-``0``/``1`` values to ``0``/``1``.

        The possible values of the *resolver* argument are:

        * ``"weak"``:
            Weak values are resolved to their strong-valued equivalents.

        * ``"zeros"``:
            ``L`` and ``H`` are resolved to ``0`` and ``1``, respectively.
            Remaining non-``0``/``1`` values are resolved to ``0``.

        * ``"ones"``:
            ``L`` and ``H`` are resolved to ``0`` and ``1``, respectively.
            Remaining non-``0``/``1`` values are resolved to ``1``.

        * ``"random"``:
            ``L`` and ``H`` are resolved to ``0`` and ``1``, respectively.
            Remaining non-``0``/``1`` values are randomly resolved to either ``0`` or ``1``.

        Args:
            resolver: How to resolve non-``0``/``1`` values. See possible values above.

        Returns:
            The resolved Logic.

        Raises:
            ValueError: Invalid *resolver* value.
            TypeError: Unsupported *value* type.
        """
        return type(self)(get_str_resolver(resolver)(str(self)))

    def __len__(self) -> int:
        return 1

    @property
    def is_resolvable(self) -> bool:
        """``True`` if value is ``0``, ``1``, ``L``, ``H``.

        .. versionadded:: 2.0
        """
        return (False, False, True, True, False, False, True, True, False)[self._repr]

    def __copy__(self) -> "Logic":
        return self

    def __deepcopy__(self, memo: Dict[int, object]) -> "Logic":
        return self


class Bit(Logic):
    """2-state digital signal value type.

    This is modeled after (System)Verilog's and VHDL's ``bit`` type.
    It can represent only the values ``0`` and ``1``.
    It can be converted to and from :class:`int`, :class:`str`, :class:`bool`, or :class:`Logic` values.

    As a subtype of :class:`!Logic`, it supports all of the same operations
    and can be used in operations interchangeably with :class:`!Logic`.

    Args:
        value: value to construct into a :class:`!Bit`.

    Raises:
        ValueError: If the value if of the correct type, but cannot be constructed into a :class:`!Bit`.
        TypeError: If the value is of a type that can't be constructed into a :class:`!Bit`.
    """

    _values = {_0, _1}
