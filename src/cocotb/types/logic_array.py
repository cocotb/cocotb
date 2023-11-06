# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import typing

from cocotb.binary import BinaryRepresentation, BinaryValue
from cocotb.types.array import Array
from cocotb.types.logic import Logic, LogicConstructibleT
from cocotb.types.range import Range

LogicT = typing.TypeVar("LogicT", bound=Logic)
S = typing.TypeVar("S")
Self = typing.TypeVar("Self", bound="LogicArray")


class LogicArray(Array[Logic]):
    r"""
    Fixed-sized, arbitrarily-indexed, array of :class:`cocotb.types.Logic`.

    .. currentmodule:: cocotb.types

    :class:`LogicArray`\ s can be constructed from either iterables of values
    constructible into :class:`Logic`: like :class:`bool`, :class:`str`, :class:`int`;
    or from integers.
    If constructed from a positive integer, an unsigned bit representation is used to
    construct the :class:`LogicArray`.
    If constructed from a negative integer, a two's complement bit representation is
    used.
    Like :class:`Array`, if no *range* argument is given, it is deduced from the length
    of the iterable or bit string used to initialize the variable.
    If a *range* argument is given, but no value,
    the array is filled with the default value of Logic().

    .. code-block:: python3

        >>> LogicArray("01XZ")
        LogicArray('01XZ', Range(3, 'downto', 0))

        >>> LogicArray([0, True, "X"])
        LogicArray('01X', Range(2, 'downto', 0))

        >>> LogicArray(0xA)  # picks smallest range that can fit the value
        LogicArray('1010', Range(3, 'downto', 0))

        >>> LogicArray(-4, Range(0, "to", 3))  # will sign-extend
        LogicArray('1100', Range(0, 'to', 3))

        >>> LogicArray(range=Range(0, "to", 3))  # default values
        LogicArray('XXXX', Range(0, 'to', 3))

    :class:`LogicArray`\ s support the same operations as :class:`Array`;
    however, it enforces the condition that all elements must be a :class:`Logic`.

    .. code-block:: python3

        >>> la = LogicArray("1010")
        >>> la[0]                               # is indexable
        Logic('0')

        >>> la[1:]                              # is slice-able
        LogicArray('10', Range(1, 'downto', 0))

        >>> Logic("0") in la                    # is a collection
        True

        >>> list(la)                            # is an iterable
        [Logic('1'), Logic('0'), Logic('1'), Logic('0')]

    When setting an element or slice, the *value* is first constructed into a
    :class:`Logic`.

    .. code-block:: python3

        >>> la = LogicArray("1010")
        >>> la[3] = "Z"
        >>> la[3]
        Logic('Z')

        >>> la[2:] = ['X', True, 0]
        >>> la
        LogicArray('ZX10', Range(3, 'downto', 0))

    :class:`LogicArray`\ s can be converted into :class:`str`\ s or :class:`int`\ s.

    .. code-block:: python3

        >>> la = LogicArray("1010")
        >>> la.binstr
        '1010'

        >>> la.integer          # uses unsigned representation
        10

        >>> la.signed_integer   # uses two's complement representation
        -6

    :class:`LogicArray`\ s also support element-wise logical operations: ``&``, ``|``,
    ``^``, and ``~``.

    .. code-block:: python3

        >>> def big_mux(a: LogicArray, b: LogicArray, sel: Logic) -> LogicArray:
        ...     s = LogicArray([sel] * len(a))
        ...     return (a & ~s) | (b & s)

        >>> la = LogicArray("0110")
        >>> p = LogicArray("1110")
        >>> sel = Logic('1')        # choose second option
        >>> big_mux(la, p, sel)
        LogicArray('1110', Range(3, 'downto', 0))

    Args:
        value: Initial value for the array.
        range: Indexing scheme of the array.

    Raises:
        ValueError: When argument values cannot be used to construct an array.
        TypeError: When invalid argument types are used.
    """

    __slots__ = ()

    @typing.overload
    def __init__(
        self,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT], BinaryValue],
        range: typing.Optional[Range],
    ):
        ...

    @typing.overload
    def __init__(
        self,
        value: typing.Union[
            int, typing.Iterable[LogicConstructibleT], BinaryValue, None
        ],
        range: Range,
    ):
        ...

    def __init__(
        self,
        value: typing.Union[
            int, typing.Iterable[LogicConstructibleT], BinaryValue, None
        ] = None,
        range: typing.Optional[Range] = None,
    ) -> None:
        if value is None and range is None:
            raise ValueError(
                "at least one of the value and range input parameters must be given"
            )
        if value is None:
            self._value = [Logic() for _ in range]
        elif isinstance(value, int):
            if value < 0:
                bitlen = int.bit_length(value + 1) + 1
            else:
                bitlen = max(1, int.bit_length(value))
            if range is None:
                self._value = [Logic(v) for v in _int_to_bitstr(value, bitlen)]
            else:
                if bitlen > len(range):
                    raise ValueError(f"{value} will not fit in {range}")
                self._value = [Logic(v) for v in _int_to_bitstr(value, len(range))]
        elif isinstance(value, typing.Iterable):
            self._value = [Logic(v) for v in value]
        elif isinstance(value, BinaryValue):
            self._value = [Logic(v) for v in value.binstr]
        else:
            raise TypeError(
                f"cannot construct {type(self).__qualname__} from value of type {type(value).__qualname__}"
            )
        if range is None:
            self._range = Range(len(self._value) - 1, "downto", 0)
        else:
            self._range = range
        if len(self._value) != len(self._range):
            raise ValueError(
                f"value of length {len(self._value)} will not fit in {self._range}"
            )

    @property
    def binstr(self) -> str:
        return "".join(str(bit) for bit in self)

    @property
    def is_resolvable(self) -> bool:
        return all(bit in (Logic(0), Logic(1)) for bit in self)

    @property
    def integer(self) -> int:
        value = 0
        for bit in self:
            value = value << 1 | int(bit)
        return value

    @property
    def signed_integer(self) -> int:
        value = self.integer
        if value >= (1 << (len(self) - 1)):
            value -= 1 << len(self)
        return value

    @typing.overload
    def __setitem__(self, item: int, value: LogicConstructibleT) -> None:
        ...

    @typing.overload
    def __setitem__(
        self, item: slice, value: typing.Iterable[LogicConstructibleT]
    ) -> None:
        ...

    def __setitem__(
        self,
        item: typing.Union[int, slice],
        value: typing.Union[LogicConstructibleT, typing.Iterable[LogicConstructibleT]],
    ) -> None:
        if isinstance(item, int):
            super().__setitem__(item, Logic(typing.cast(LogicConstructibleT, value)))
        elif isinstance(item, slice):
            super().__setitem__(
                item,
                (
                    Logic(v)
                    for v in typing.cast(typing.Iterable[LogicConstructibleT], value)
                ),
            )
        else:
            raise TypeError(
                f"indexes must be ints or slices, not {type(item).__name__}"
            )

    def __repr__(self) -> str:
        return "{}({!r}, {!r})".format(type(self).__qualname__, self.binstr, self.range)

    def __and__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise & "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return type(self)(a & b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __rand__(self: Self, other: Self) -> Self:
        return self & other

    def __or__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise | "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return type(self)(a | b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __ror__(self: Self, other: Self) -> Self:
        return self | other

    def __xor__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise ^ "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return type(self)(a ^ b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __rxor__(self: Self, other: Self) -> Self:
        return self ^ other

    def __invert__(self: Self) -> Self:
        return type(self)(~v for v in self)

    def to_BinaryValue(
        self,
        bigEndian: bool = True,
        binaryRepresentation: BinaryRepresentation = BinaryRepresentation.UNSIGNED,
    ) -> BinaryValue:
        return BinaryValue(
            value=self.binstr,
            n_bits=len(self),
            bigEndian=bigEndian,
            binaryRepresentation=binaryRepresentation,
        )


def _int_to_bitstr(value: int, n_bits: int) -> str:
    if value < 0:
        value += 1 << n_bits
    return format(value, f"0{n_bits}b")
