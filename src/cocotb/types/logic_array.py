# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import typing
import warnings

from cocotb._deprecation import deprecated
from cocotb.types import ArrayLike
from cocotb.types.logic import Logic, LogicConstructibleT
from cocotb.types.range import Range


class LogicArray(ArrayLike[Logic]):
    r"""
    Fixed-sized, arbitrarily-indexed, array of :class:`cocotb.types.Logic`.

    .. currentmodule:: cocotb.types

    :class:`LogicArray`\ s can be constructed from either iterables of values
    constructible into :class:`Logic`: like :class:`bool`, :class:`str`, :class:`int`.
    Like :class:`Array`, if no *range* argument is given, it is deduced from the length
    of the iterable used to initialize the variable.
    If a *range* argument is given, but no value,
    the array is filled with the default value of ``Logic()``.

    .. code-block:: python3

        >>> LogicArray("01XZ")
        LogicArray('01XZ', Range(3, 'downto', 0))

        >>> LogicArray([0, True, "X"])
        LogicArray('01X', Range(2, 'downto', 0))

        >>> LogicArray(range=Range(0, "to", 3))  # default values
        LogicArray('XXXX', Range(0, 'to', 3))

    :class:`LogicArray`\ s can be constructed from :class:`int`\ s using :meth:`from_unsigned` or :meth:`from_signed`.

    .. code-block:: python3

        >>> LogicArray.from_unsigned(0xA)  # picks smallest range that can fit the value
        LogicArray('1010', Range(3, 'downto', 0))

        >>> LogicArray.from_signed(-4, Range(0, "to", 3))  # will sign-extend
        LogicArray('1100', Range(0, 'to', 3))

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
        >>> str(la)
        '1010'

        >>> la.to_unsigned()
        10

        >>> la.to_signed()
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
        OverflowError: When given *value* cannot fit in given *range*.
        ValueError: When argument values cannot be used to construct an array.
        TypeError: When invalid argument types are used.
    """

    _value: typing.List[Logic]
    _range: Range

    @typing.overload
    def __new__(
        cls,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT]],
        range: typing.Optional[Range] = None,
    ) -> "LogicArray": ...

    @typing.overload
    def __new__(
        cls,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT], None] = None,
        *,
        range: Range,
    ) -> "LogicArray": ...

    def __new__(
        cls,
        value: typing.Union[int, typing.Iterable[LogicConstructibleT], None] = None,
        range: typing.Optional[Range] = None,
    ) -> "LogicArray":
        if isinstance(value, int):
            warnings.warn(
                "Constructing a LogicArray from an integer is deprecated. "
                "Use `LogicArray.from_signed(value)` or `LogicArray.from_unsigned(value)` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            if value < 0:
                return cls.from_signed(value, range=range)
            else:
                return cls.from_unsigned(value, range=range)

        self = super().__new__(cls)

        # construct _value representation
        if value is None:
            if range is None:
                raise ValueError(
                    "at least one of the value and range input parameters must be given"
                )
            self._value = [Logic() for _ in range]
        else:
            value_iter = iter(value)
            self._value = [Logic(v) for v in value_iter]

        # construct _range representation
        if range is None:
            self._range = Range(len(self._value) - 1, "downto", 0)
        else:
            self._range = range

        # check that _value and _range align
        if len(self._value) != len(self._range):
            raise OverflowError(
                f"value of length {len(self._value)} will not fit in {self._range}"
            )

        return self

    @classmethod
    def from_unsigned(
        cls, value: int, range: typing.Optional[Range] = None
    ) -> "LogicArray":
        """Construct a :class:`LogicArray` from an :class:`int` by interpreting it as a bit vector with unsigned representation.

        The :class:`int` is treated as an arbitrary-length bit vector with unsigned representation where the left-most bit is the most significant bit.
        This bit vector is then constructed into a :class:`LogicArray`.

        If *range* is not given, it defaults to ``Range(n_bits-1, "downto", 0)``,
        where ``n_bits`` is the minimum number of bits necessary to hold the value.

        If *range* is given and the value cannot fit in a :class:`LogicArray` of that size,
        an :exc:`OverflowError` is raised.

        Args:
            value: The integer to convert.
            range: A specific :class:`Range` to use as the bounds on the return :class:`LogicArray` object.

        Returns:
            A :class:`LogicArray` equivalent to the *value* by interpreting it as a bit vector with unsigned representation.

        Raises:
            OverflowError: When a :class:`LogicArray` of the given *range* can't hold the *value*.
        """
        if value < 0:
            raise OverflowError(f"{value} not in bounds for an unsigned integer.")

        bitlen = max(1, int.bit_length(value))

        if range is None:
            range = Range(bitlen - 1, "downto", 0)
        elif bitlen > len(range):
            raise OverflowError(
                f"{value} will not fit in a LogicArray with bounds: {range!r}."
            )

        return LogicArray(_int_to_bitstr(value, len(range)), range=range)

    @classmethod
    def from_signed(
        cls, value: int, range: typing.Optional[Range] = None
    ) -> "LogicArray":
        """Construct a :class:`LogicArray` from an :class:`int` by interpreting it as a bit vector with two's complement representation.

        The :class:`int` is treated as an arbitrary-length bit vector with two's complement representation where the left-most bit is the most significant bit.
        This bit vector is then constructed into a :class:`LogicArray`.

        If *range* is not given, it defaults to ``Range(n_bits-1, "downto", 0)``,
        where ``n_bits`` is the minimum number of bits necessary to hold the value.

        If *range* is given and the value cannot fit in a :class:`LogicArray` of that size,
        an :exc:`OverflowError` is raised.

        Args:
            value: The integer to convert.
            range: A specific :class:`Range` to use as the bounds on the return :class:`LogicArray` object.

        Returns:
            A :class:`LogicArray` equivalent to the *value* by interpreting it as a bit vector with two's complement representation.

        Raises:
            OverflowError: When a :class:`LogicArray` of the given *range* can't hold the *value*.
        """
        bitlen = int.bit_length(value + 1) + 1

        if range is None:
            range = Range(bitlen - 1, "downto", 0)
        elif bitlen > len(range):
            raise OverflowError(
                f"{value} will not fit in a LogicArray with bounds: {range!r}."
            )

        return LogicArray(_int_to_bitstr(value, len(range)), range=range)

    @property
    def range(self) -> Range:
        """:class:`Range` of the indexes of the array."""
        return self._range

    @range.setter
    def range(self, new_range: Range) -> None:
        """Set a new indexing scheme on the array. Must be the same size."""
        if not isinstance(new_range, Range):
            raise TypeError("range argument must be of type 'Range'")
        if len(new_range) != len(self):
            raise ValueError(
                f"{new_range!r} not the same length as old range: {self._range!r}."
            )
        self._range = new_range

    def __iter__(self) -> typing.Iterator[Logic]:
        return iter(self._value)

    def __reversed__(self) -> typing.Iterator[Logic]:
        return reversed(self._value)

    def __contains__(self, item: object) -> bool:
        return item in self._value

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if isinstance(other, LogicArray):
            return self._value == other._value
        elif isinstance(other, int):
            try:
                return self.to_unsigned() == other
            except ValueError:
                return False
        elif isinstance(other, (str, list, tuple)):
            try:
                other = LogicArray(other)
            except ValueError:
                return False
            return self == other
        else:
            return NotImplemented

    def count(self, value: Logic) -> int:
        """Return number of occurrences of *value*."""
        return self._value.count(value)

    @property
    @deprecated("`.binstr` property is deprecated. Use `str(value)` instead.")
    def binstr(self) -> str:
        """Convert the value to the :class:`str` literal representation.

        .. deprecated:: 2.0
        """
        return str(self)

    @property
    def is_resolvable(self) -> bool:
        """``True`` if all elements are ``0`` or ``1``."""
        return all(bit in (Logic(0), Logic(1)) for bit in self)

    @property
    @deprecated("`.integer` property is deprecated. Use `value.to_unsigned()` instead.")
    def integer(self) -> int:
        """Convert the value to an :class:`int` by interpreting it using unsigned representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using unsigned representation.

        Returns: An :class:`int` equivalent to the value by interpreting it using unsigned representation.

        .. deprecated:: 2.0
        """
        return self.to_unsigned()

    @property
    @deprecated(
        "`.signed_integer` property is deprecated. Use `value.to_signed()` instead."
    )
    def signed_integer(self) -> int:
        """Convert the value to an :class:`int` by interpreting it using two's complement representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using two's complement representation.

        Returns: An :class:`int` equivalent to the value by interpreting it using two's complement representation.

        .. deprecated:: 2.0
        """
        return self.to_signed()

    def to_unsigned(self) -> int:
        """Convert the value to an :class:`int` by interpreting it using unsigned representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using unsigned representation.

        Returns: An :class:`int` equivalent to the value by interpreting it using unsigned representation.
        """
        value = 0
        for bit in self:
            value = value << 1 | int(bit)
        return value

    def to_signed(self) -> int:
        """Convert the value to an :class:`int` by interpreting it using two's complement representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using two's complement representation.

        Returns: An :class:`int` equivalent to the value by interpreting it using two's complement representation.
        """
        value = self.to_unsigned()
        if value >= (1 << (len(self) - 1)):
            value -= 1 << len(self)
        return value

    @typing.overload
    def __getitem__(self, item: int) -> Logic: ...

    @typing.overload
    def __getitem__(self, item: slice) -> "LogicArray": ...

    def __getitem__(
        self, item: typing.Union[int, slice]
    ) -> typing.Union[Logic, "LogicArray"]:
        if isinstance(item, int):
            idx = self._translate_index(item)
            return self._value[idx]
        elif isinstance(item, slice):
            start = item.start if item.start is not None else self.left
            stop = item.stop if item.stop is not None else self.right
            if item.step is not None:
                raise IndexError("do not specify step")
            start_i = self._translate_index(start)
            stop_i = self._translate_index(stop)
            if start_i > stop_i:
                raise IndexError(
                    f"slice [{start}:{stop}] direction does not match array direction [{self.left}:{self.right}]"
                )
            value = self._value[start_i : stop_i + 1]
            range = Range(start, self.direction, stop)
            return LogicArray(value=value, range=range)
        raise TypeError(f"indexes must be ints or slices, not {type(item).__name__}")

    @typing.overload
    def __setitem__(self, item: int, value: LogicConstructibleT) -> None: ...

    @typing.overload
    def __setitem__(
        self, item: slice, value: typing.Iterable[LogicConstructibleT]
    ) -> None: ...

    def __setitem__(
        self,
        item: typing.Union[int, slice],
        value: typing.Union[LogicConstructibleT, typing.Iterable[LogicConstructibleT]],
    ) -> None:
        if isinstance(item, int):
            idx = self._translate_index(item)
            self._value[idx] = Logic(typing.cast(LogicConstructibleT, value))
        elif isinstance(item, slice):
            start = item.start if item.start is not None else self.left
            stop = item.stop if item.stop is not None else self.right
            if item.step is not None:
                raise IndexError("do not specify step")
            start_i = self._translate_index(start)
            stop_i = self._translate_index(stop)
            if start_i > stop_i:
                raise IndexError(
                    f"slice [{start}:{stop}] direction does not match array direction [{self.left}:{self.right}]"
                )
            value_as_logics = [
                Logic(v)
                for v in typing.cast(typing.Iterable[LogicConstructibleT], value)
            ]
            if len(value_as_logics) != (stop_i - start_i + 1):
                raise ValueError(
                    f"value of length {len(value_as_logics)!r} will not fit in slice [{start}:{stop}]"
                )
            self._value[start_i : stop_i + 1] = value_as_logics
        else:
            raise TypeError(
                f"indexes must be ints or slices, not {type(item).__name__}"
            )

    def _translate_index(self, item: int) -> int:
        try:
            return self._range.index(item)
        except ValueError:
            raise IndexError(f"index {item} out of range") from None

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({str(self)!r}, {self.range!r})"

    def __str__(self) -> str:
        return "".join(str(bit) for bit in self)

    def __int__(self) -> int:
        return self.to_unsigned()

    def __and__(self, other: "LogicArray") -> "LogicArray":
        if isinstance(other, LogicArray):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise & "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return LogicArray(a & b for a, b in zip(self, other))
        return NotImplemented

    def __or__(self, other: "LogicArray") -> "LogicArray":
        if isinstance(other, LogicArray):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise | "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return LogicArray(a | b for a, b in zip(self, other))
        return NotImplemented

    def __xor__(self, other: "LogicArray") -> "LogicArray":
        if isinstance(other, LogicArray):
            if len(self) != len(other):
                raise ValueError(
                    f"cannot perform bitwise ^ "
                    f"between {type(self).__qualname__} of length {len(self)} "
                    f"and {type(other).__qualname__} of length {len(other)}"
                )
            return LogicArray(a ^ b for a, b in zip(self, other))
        return NotImplemented

    def __invert__(self) -> "LogicArray":
        return LogicArray(~v for v in self)


def _int_to_bitstr(value: int, n_bits: int) -> str:
    if value < 0:
        value += 1 << n_bits
    return format(value, f"0{n_bits}b")
