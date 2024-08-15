# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import warnings
from math import ceil
from typing import (
    TYPE_CHECKING,
    Iterable,
    Iterator,
    List,
    Optional,
    Union,
    cast,
    overload,
)

from cocotb._deprecation import deprecated
from cocotb.types import ArrayLike
from cocotb.types.logic import Logic, LogicConstructibleT, _str_literals
from cocotb.types.range import Range

if TYPE_CHECKING:  # pragma: no cover
    from typing import Literal


class LogicArray(ArrayLike[Logic]):
    r"""Fixed-sized, arbitrarily-indexed, array of :class:`cocotb.types.Logic`.

    .. currentmodule:: cocotb.types

    :class:`LogicArray`\ s can be constructed from iterables of values
    constructible into :class:`Logic` like :class:`bool`, :class:`str`, :class:`int`,
    or it can be constructed :class:`str` or :class:`int` literals syntaxes, as seen below.

    Like :class:`Array`, if no *range* argument is given, it is deduced from the length
    of the iterable used to initialize the variable.

    If a *range* argument is given, but no value,
    the array is filled with the default value of ``Logic()``.

    .. code-block:: python3

        >>> LogicArray(0b0111, Range(3, "downto", 0))
        LogicArray('0111', Range(3, 'downto', 0))

        >>> LogicArray("01XZ")
        LogicArray('01XZ', Range(3, 'downto', 0))

        >>> LogicArray([0, True, "X"])
        LogicArray('01X', Range(2, 'downto', 0))

        >>> LogicArray(range=Range(0, "to", 3))  # default values
        LogicArray('XXXX', Range(0, 'to', 3))

    :class:`LogicArray`\ s can be constructed from :class:`int`\ s using :meth:`from_unsigned` or :meth:`from_signed`.

    .. code-block:: python3

        >>> LogicArray.from_unsigned(0xA, Range(3, 'downto', 0))
        LogicArray('1010', Range(3, 'downto', 0))

        >>> LogicArray.from_signed(-4, Range(0, "to", 3))  # will sign-extend
        LogicArray('1100', Range(0, 'to', 3))

    :class:`LogicArray`\ s can be constructed from :class:`bytes` or :class:`bytearray` using :meth:`from_bytes`.
    Use the *byteorder* argument to control endianness; it defaults to ``"big"``.

    .. code-block:: python3

        >>> LogicArray.from_bytes(b"1n")
        LogicArray('0011000101101110', Range(15, 'downto', 0))

        >>> LogicArray.from_bytes(b"1n", byteorder="little")
        LogicArray('0110111000110001', Range(15, 'downto', 0))

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

    :class:`LogicArray`\ s can be converted into :class:`str`\ s, :class:`int`\ s, or :class:`bytes`\ s.

    .. code-block:: python3

        >>> la = LogicArray("1010")
        >>> str(la)
        '1010'

        >>> la.to_unsigned()
        10

        >>> la.to_signed()
        -6

        >>> la.to_bytes()
        b"\n"

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

    # These three attribute contain the current value of the array in one or more of
    # three different implementations. This is done for performance reasons, as certain
    # implementations are faster for particular operations.
    # Each implementation can be present, or None if the implementation has not been
    # computed or has been invalidated by a mutating operation.
    _value_as_array: Union[List[Logic], None]
    _value_as_int: Union[int, None]
    _value_as_str: Union[str, None]
    _range: Range

    @overload
    def __init__(
        self,
        value: str,
        range: Optional[Range] = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        value: Iterable[LogicConstructibleT],
        range: Optional[Range] = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        value: int,
        range: Range,
    ) -> None: ...

    @overload
    def __init__(
        self,
        value: None,
        range: Range,
    ) -> None: ...

    def __init__(
        self,
        value: Union[int, str, Iterable[LogicConstructibleT], None] = None,
        range: Optional[Range] = None,
    ) -> None:
        self._value_as_array = None
        self._value_as_int = None
        self._value_as_str = None
        if range is not None and not isinstance(range, Range):
            raise TypeError(
                f"Expected Range for parameter 'range', not {type(range).__qualname__}"
            )
        if isinstance(value, str):
            if not (set(value) <= _str_literals):
                raise ValueError("Invalid str literal")
            self._value_as_str = value.upper()
            if range is not None:
                if len(value) != len(range):
                    raise OverflowError(
                        f"Value of length {len(self._value_as_str)} will not fit in {range}"
                    )
                self._range = range
            else:
                self._range = Range(len(self._value_as_str) - 1, "downto", 0)
        elif isinstance(value, int):
            if value < 0:
                raise ValueError("Invalid int literal")
            if range is None:
                raise TypeError("Missing required argument: 'range'")
            bitlen = max(1, int.bit_length(value))
            if bitlen > len(range):
                raise OverflowError(
                    f"{value} will not fit in a LogicArray with bounds: {range!r}."
                )
            self._value_as_int = value
            self._range = range
        elif value is None:
            if range is None:
                raise TypeError("Missing required argument: 'range'")
            self._value_as_str = "X" * len(range)
            self._range = range
        else:
            self._value_as_array = [Logic(v) for v in value]
            if range is not None:
                if len(self._value_as_array) != len(range):
                    raise OverflowError(
                        f"Value of length {len(self._value_as_array)} will not fit in {range}"
                    )
                self._range = range
            else:
                self._range = Range(len(self._value_as_array) - 1, "downto", 0)

    def _get_array(self) -> List[Logic]:
        if self._value_as_array is None:
            # May convert int to str before to converting to array.
            self._value_as_array = [Logic(v) for v in self._get_str()]
        return self._value_as_array

    def _get_str(self) -> str:
        if self._value_as_str is None:
            if self._value_as_int is not None:
                self._value_as_str = format(self._value_as_int, f"0{len(self)}b")
            else:
                self._value_as_str = "".join(
                    str(v) for v in cast(List[Logic], self._value_as_array)
                )
        return self._value_as_str

    def _get_int(self) -> int:
        if self._value_as_int is None:
            # May convert list to str before converting to int.
            self._value_as_int = int(self._get_str(), 2)
        return self._value_as_int

    @classmethod
    def from_unsigned(cls, value: int, range: Range) -> "LogicArray":
        """Construct a :class:`LogicArray` from an :class:`int` by interpreting it as a bit vector with unsigned representation.

        The :class:`int` is treated as an arbitrary-length bit vector with unsigned representation where the left-most bit is the most significant bit.
        This bit vector is then constructed into a :class:`LogicArray`.

        Args:
            value: The integer to convert.
            range: A specific :class:`Range` to use as the bounds on the return :class:`LogicArray` object.

        Returns:
            A :class:`LogicArray` equivalent to the *value* by interpreting it as a bit vector with unsigned representation.

        Raises:
            OverflowError: When a :class:`LogicArray` of the given *range* can't hold the *value*.
        """
        return LogicArray(value, range=range)

    @classmethod
    def from_signed(cls, value: int, range: Range) -> "LogicArray":
        """Construct a :class:`LogicArray` from an :class:`int` by interpreting it as a bit vector with two's complement representation.

        The :class:`int` is treated as an arbitrary-length bit vector with two's complement representation where the left-most bit is the most significant bit.
        This bit vector is then constructed into a :class:`LogicArray`.

        Args:
            value: The integer to convert.
            range: A specific :class:`Range` to use as the bounds on the return :class:`LogicArray` object.

        Returns:
            A :class:`LogicArray` equivalent to the *value* by interpreting it as a bit vector with two's complement representation.

        Raises:
            OverflowError: When a :class:`LogicArray` of the given *range* can't hold the *value*.
        """
        if value < 0:
            value += 2 ** len(range)
        # If value doesn't fit in range, it will still be negative and will blow the
        # constructor up in a bad way.
        if value < 0:
            raise OverflowError(
                f"{value} will not fit in a LogicArray with bounds: {range!r}."
            )
        return LogicArray(value, range=range)

    @classmethod
    def from_bytes(
        cls,
        value: Union[bytes, bytearray],
        range: Optional[Range] = None,
        byteorder: "Literal['big'] | Literal['little']" = "big",
    ) -> "LogicArray":
        """Construct a :class:`LogicArray` from :class:`bytes`.

        The :class:`bytes` is first converted to an unsigned integer using *byteorder*-endian representation,
        then is converted to a :class:`LogicArray` as in :meth:`from_unsigned`.

        Args:
            value: The bytes to convert.
            range: A specific :class:`Range` to use as the bounds. Defaults to ``Range(len(value) * 8 - 1, "downto", 0)``.
            byteorder: The endianness used to construct the intermediate integer, either ``"big"`` or ``"little"``.

        Returns:
            A :class:`LogicArray` equivalent to the *value* by interpreting it as an unsigned integer in big-endian representation.

        Raises:
            OverflowError: When a :class:`LogicArray` of the given *range* can't hold the *value*.
        """
        if range is None:
            range = Range(len(value) * 8 - 1, "downto", 0)
        elif len(value) * 8 != len(range):
            raise OverflowError(f"Value of length {len(value)} will not fit in {range}")
        return cls.from_unsigned(
            int.from_bytes(value, byteorder=byteorder, signed=False), range=range
        )

    @classmethod
    def _from_handle(cls, value: str) -> "LogicArray":
        # Used by cocotb.handle classes to make LogicArray from values gotten from the
        # simulator which we expect to be well-formed.
        # Values are required to be uppercase.
        self = super().__new__(cls)
        self._value_as_array = None
        self._value_as_int = None
        self._value_as_str = value
        self._range = Range(len(value) - 1, "downto", 0)
        return self

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

    def __iter__(self) -> Iterator[Logic]:
        return iter(self._get_array())

    def __reversed__(self) -> Iterator[Logic]:
        return reversed(self._get_array())

    def __contains__(self, item: object) -> bool:
        return item in self._get_array()

    def __eq__(
        self,
        other: object,
    ) -> bool:
        if isinstance(other, int):
            try:
                return self.to_unsigned() == other
            except ValueError:
                return False
        elif isinstance(other, str):
            return str(self) == other.upper()
        elif isinstance(other, LogicArray):
            if len(self) != len(other):
                return False
            # Complex, but efficient chain of checking logic.
            # Avoid conversions if it can help it at first.
            # Prefers checking against str vs any type since that is going to be the
            #   most common type and also the "middle" type for conversions.
            # Always converts away from ints to prevent issues with non-0/1 data.
            if self._value_as_str is not None and other._value_as_str is not None:
                # (STR, STR)
                return self._value_as_str == other._value_as_str
            elif self._value_as_array is not None and other._value_as_array is not None:
                # (ARRAY, ARRAY)
                return self._value_as_array == other._value_as_array
            elif self._value_as_int is not None and other._value_as_int is not None:
                # (INT, INT)
                return self._value_as_int == other._value_as_int
            elif self._value_as_str is not None:
                # (STR, INT)
                # (STR, ARRAY)
                return self._value_as_str == other._get_str()
            elif other._value_as_str is not None:
                # (INT, STR)
                # (ARRAY, STR)
                return self._get_str() == other._value_as_str
            elif self._value_as_array is not None:
                # (ARRAY, INT)
                return self._value_as_array == other._get_array()
            else:
                # (INT, ARRAY)
                return self._get_array() == other._value_as_array
        elif isinstance(other, (list, tuple)):
            try:
                other = LogicArray(other)
            except ValueError:
                return False
            return self == other
        else:
            return NotImplemented

    def count(self, value: Logic) -> int:
        """Return number of occurrences of *value*."""
        return self._get_array().count(value)

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

    @property
    @deprecated("`.buff` property is deprecated. Use `v.to_bytes()` instead.")
    def buff(self) -> bytes:
        """Convert the value to :class:`bytes` by interpreting it as an unsigned integer in big-endian byte order.

        The object is first converted to an :class:`int` as in :meth:`to_unsigned`.
        Then the object is converted to :class:`bytes` by converting the resulting integer value as in :meth:`int.to_bytes`.
        This assumes big-endian byte order and the minimal number of bytes necessary to hold any value of the current object.

        Returns: A :class:`bytes` object equivalent to the value.

        .. deprecated:: 2.0
        """
        return self.to_bytes()

    def to_unsigned(self) -> int:
        """Convert the value to an :class:`int` by interpreting it using unsigned representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using unsigned representation.

        Returns: An :class:`int` equivalent to the value by interpreting it using unsigned representation.
        """
        if len(self) == 0:
            warnings.warn("Converting a LogicArray of length 0 to integer")
            return 0
        return self._get_int()

    def to_signed(self) -> int:
        """Convert the value to an :class:`int` by interpreting it using two's complement representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using two's complement representation.

        Returns: An :class:`int` equivalent to the value by interpreting it using two's complement representation.
        """
        if len(self) == 0:
            warnings.warn("Converting a LogicArray of length 0 to integer")
            return 0
        value = self._get_int()
        if value >= (1 << (len(self) - 1)):
            value -= 1 << len(self)
        return value

    def to_bytes(
        self,
        byteorder: "Literal['big'] | Literal['little']" = "big",
    ) -> bytes:
        """Convert the value to :class:`bytes`.

        The :class:`LogicArray` is converted to an unsigned integer as in :meth:`to_unsigned`,
        then is converted to :class:`bytes` using *byteorder*-endian representation
        with the minimum number of bytes which can store all the bits in the original :class:`LogicArray`.

        Args:
            byteorder: The endianness used to construct the intermediate integer, either ``"big"`` or ``"little"``.

        Returns:
            :class:`bytes` equivalent to the value.
        """
        return self.to_unsigned().to_bytes(ceil(len(self) / 8), byteorder=byteorder)

    @overload
    def __getitem__(self, item: int) -> Logic: ...

    @overload
    def __getitem__(self, item: slice) -> "LogicArray": ...

    def __getitem__(self, item: Union[int, slice]) -> Union[Logic, "LogicArray"]:
        array = self._get_array()
        if isinstance(item, int):
            idx = self._translate_index(item)
            return array[idx]
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
            value = array[start_i : stop_i + 1]
            range = Range(start, self.direction, stop)
            return LogicArray(value=value, range=range)
        raise TypeError(f"indexes must be ints or slices, not {type(item).__name__}")

    @overload
    def __setitem__(self, item: int, value: LogicConstructibleT) -> None: ...

    @overload
    def __setitem__(
        self, item: slice, value: Iterable[LogicConstructibleT]
    ) -> None: ...

    def __setitem__(
        self,
        item: Union[int, slice],
        value: Union[LogicConstructibleT, Iterable[LogicConstructibleT]],
    ) -> None:
        array = self._get_array()
        # invalid other impls
        self._value_as_str = None
        self._value_as_int = None
        if isinstance(item, int):
            idx = self._translate_index(item)
            array[idx] = Logic(cast(LogicConstructibleT, value))
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
                Logic(v) for v in cast(Iterable[LogicConstructibleT], value)
            ]
            if len(value_as_logics) != (stop_i - start_i + 1):
                raise ValueError(
                    f"value of length {len(value_as_logics)!r} will not fit in slice [{start}:{stop}]"
                )
            array[start_i : stop_i + 1] = value_as_logics
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
        return self._get_str()

    def __int__(self) -> int:
        return self.to_unsigned()

    def __and__(self, other: "LogicArray") -> "LogicArray":
        if not isinstance(other, LogicArray):
            return NotImplemented
        if len(self) != len(other):
            raise ValueError(
                f"cannot perform bitwise & "
                f"between {type(self).__qualname__} of length {len(self)} "
                f"and {type(other).__qualname__} of length {len(other)}"
            )
        return LogicArray(a & b for a, b in zip(self, other))

    def __or__(self, other: "LogicArray") -> "LogicArray":
        if not isinstance(other, LogicArray):
            return NotImplemented
        if len(self) != len(other):
            raise ValueError(
                f"cannot perform bitwise | "
                f"between {type(self).__qualname__} of length {len(self)} "
                f"and {type(other).__qualname__} of length {len(other)}"
            )
        return LogicArray(a | b for a, b in zip(self, other))

    def __xor__(self, other: "LogicArray") -> "LogicArray":
        if not isinstance(other, LogicArray):
            return NotImplemented
        if len(self) != len(other):
            raise ValueError(
                f"cannot perform bitwise ^ "
                f"between {type(self).__qualname__} of length {len(self)} "
                f"and {type(other).__qualname__} of length {len(other)}"
            )
        return LogicArray(a ^ b for a, b in zip(self, other))

    def __invert__(self) -> "LogicArray":
        return LogicArray(~v for v in self)
