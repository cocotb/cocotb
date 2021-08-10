# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import typing

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

    Supports all of the same operations as :class:`Array`;
    however, it enforces the condition that all elements must be a :class:`Logic`.
    When constructing a :class:`LogicArray`, or setting a slice,
    the *value* is treated as an iterable of values that are constructed into :class:`Logic`\ s.
    Also, when setting an element, the *value* is first constructed into a :class:`Logic`.

    .. code-block:: python3

        >>> l = LogicArray("01XZ")
        >>> l[0]
        Logic('0')

        >>> l[0] = "Z"
        >>> l[0]
        Logic('Z')

        >>> l[:2] = [True, 'X', 0]
        >>> l
        LogicArray('1X0Z', Range(0, 'to', 3))

    Support element-wise logical operations: ``&``, ``|``, ``^``, and ``~``.

    .. code-block:: python3

        >>> def big_mux(a: LogicArray, b: LogicArray, sel: Logic) -> LogicArray:
        ...     s = LogicArray([sel] * len(a))
        ...     return (a & ~s) | (b & s)

        >>> l = LogicArray("0110")
        >>> p = LogicArray("1110")
        >>> sel = Logic('1')       # choose second option
        >>> big_mux(l, p, sel)
        LogicArray('1110', Range(0, 'to', 3))

    Args:
        value: Initial value for the array.
        range: Indexing scheme of the array.

    Raises:
        ValueError: When argument values cannot be used to construct an array.
        TypeError: When invalid argument types are used.
    """

    __slots__ = ()

    def __init__(
        self,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT]],
        range: typing.Optional[Range] = None,
    ) -> None:
        if isinstance(value, int):
            if value < 0:
                bitlen = int.bit_length(value + 1) + 1
            else:
                bitlen = max(1, int.bit_length(value))
            if range is None:
                value = _int_to_bitstr(value, bitlen)
                range = Range(bitlen-1, "downto", 0)
            elif bitlen > len(range):
                raise ValueError(f"{value} will not fit in {range}")
            else:
                value = _int_to_bitstr(value, len(range))

        super().__init__(
            value=(Logic(v) for v in value),
            range=range,
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
                "indexes must be ints or slices, not {}".format(type(item).__name__)
            )

    def __repr__(self) -> str:
        return "{}({!r}, {!r})".format(type(self).__qualname__, self.binstr, self.range)

    def __and__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    "cannot perform bitwise & on arrays of different length"
                )
            return type(self)(a & b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __rand__(self: Self, other: Self) -> Self:
        return self & other

    def __or__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    "cannot perform bitwise | on arrays of different length"
                )
            return type(self)(a | b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __ror__(self: Self, other: Self) -> Self:
        return self | other

    def __xor__(self: Self, other: Self) -> Self:
        if isinstance(other, type(self)):
            if len(self) != len(other):
                raise ValueError(
                    "cannot perform bitwise ^ on arrays of different length"
                )
            return type(self)(a ^ b for a, b in zip(self, other))  # type: ignore
        return NotImplemented

    def __rxor__(self: Self, other: Self) -> Self:
        return self ^ other

    def __invert__(self: Self) -> Self:
        return type(self)(~v for v in self)


def _int_to_bitstr(value: int, bit_length: int) -> str:
    if value < 0:
        value += 1 << bit_length
    return format(value, f"0{bit_length}b")
