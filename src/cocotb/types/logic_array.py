# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
import random
import warnings
from math import ceil
from typing import (
    TYPE_CHECKING,
    Dict,
    Iterable,
    Iterator,
    List,
    Union,
    cast,
    overload,
)

from cocotb._deprecation import deprecated
from cocotb._utils import DocStrEnum
from cocotb.types import ArrayLike
from cocotb.types.logic import Logic, LogicConstructibleT, _str_literals
from cocotb.types.range import Range

if TYPE_CHECKING:
    from typing import Literal


class ResolveX(DocStrEnum):
    """Resolution behaviors supported when converting a :class:`LogicArray` to an integer.

    The values ``L`` and ``H`` are always resolved to ``0`` and ``1`` respectively.
    These behaviors exist to resolve the Logic values ``X``, ``Z``, ``U``, ``W``, and ``-``
    to either ``0`` or ``1``.
    """

    VALUE_ERROR = (
        "error",
        "Throws a :exc:`ValueError` if the :class:`LogicArray` contains non-``0``/``1`` values.",
    )
    ZEROS = ("zeros", "Resolves all non-``0``/``1`` values to ``0``.")
    ONES = ("ones", "Resolves all non-``0``/``1`` values to ``1``.")
    RANDOM = (
        "random",
        "Resolves all non-``0``/``1`` values randomly to either ``0`` or ``1``.",
    )


RESOLVE_X = ResolveX[os.getenv("COCOTB_RESOLVE_X", "VALUE_ERROR")]
"""Global default for resolving ``X``, ``Z``, ``U``, ``W``, and ``-`` values to ``0`` or ``1``.

Set using :envvar:`COCOTB_RESOLVE_X` before boot, or via this variable any time thereafter.
Defaults to :attr:`~ResolveX.VALUE_ERROR`.

.. warning::

    This exists for backwards-compatibility reasons.
    Using any value besides ``VALUE_ERROR`` is *not* recommended.
"""


_resolve_lh_table = str.maketrans({"L": "0", "H": "1"})

_ord_0 = ord("0")


class _error_resolve_table(Dict[int, int]):
    def __init__(self) -> None:
        self.update({ord(c): ord(c) for c in "01"})

    def __missing__(self, key: str) -> int:
        raise ValueError(f"Unresolvable bit in binary string: {key!r}.")


class _random_resolve_table(Dict[int, int]):
    def __init__(self) -> None:
        self.update({ord(c): ord(c) for c in "01"})

    def __missing__(self, _: str) -> int:
        return random.getrandbits(1) + _ord_0


_resolve_tables = {
    "error": _error_resolve_table(),
    "zeros": str.maketrans("XZUW-", "00000"),
    "ones": str.maketrans("XZUW-", "11111"),
    "random": _random_resolve_table(),
}


class LogicArray(ArrayLike[Logic]):
    r"""Fixed-sized, arbitrarily-indexed, array of :class:`cocotb.types.Logic`.

    .. currentmodule:: cocotb.types

    :class:`LogicArray`\ s can be constructed from iterables of values
    constructible into :class:`Logic` like :class:`bool`, :class:`str`, :class:`int`,
    or it can be constructed :class:`str` or :class:`int` literals syntaxes, as seen below.

    Like :class:`Array`, if *range* is not given, the range ``Range(len(value)-1, "downto", 0)`` is used.
    If an :class:`int` is passed for *range*, the range ``Range(range-1, "downto", 0)`` is used.

    .. code-block:: pycon3

        >>> LogicArray(0b0111, 4)
        LogicArray('0111', Range(3, 'downto', 0))

        >>> LogicArray("01XZ")
        LogicArray('01XZ', Range(3, 'downto', 0))

        >>> LogicArray([0, True, "X"])
        LogicArray('01X', Range(2, 'downto', 0))

    .. note::
        If constructing from an unsigned :class:`int` literal, *range* `must` be given.

    :class:`LogicArray`\ s can be constructed from :class:`int`\ s using :meth:`from_unsigned` or :meth:`from_signed`.

    .. code-block:: pycon3

        >>> LogicArray.from_unsigned(0xA, 4)
        LogicArray('1010', Range(3, 'downto', 0))

        >>> LogicArray.from_signed(-4, Range(0, "to", 3))  # will sign-extend
        LogicArray('1100', Range(0, 'to', 3))

    :class:`LogicArray`\ s can be constructed from :class:`bytes` or :class:`bytearray` using :meth:`from_bytes`.
    Use the *byteorder* argument to control endianness.

    .. code-block:: pycon3

        >>> LogicArray.from_bytes(b"1n", byteorder="big")
        LogicArray('0011000101101110', Range(15, 'downto', 0))

        >>> LogicArray.from_bytes(b"1n", byteorder="little")
        LogicArray('0110111000110001', Range(15, 'downto', 0))

    :class:`LogicArray`\ s support the same :class:`list`-like operations as :class:`Array`;
    however, it enforces the condition that all elements must be a :class:`Logic`.

    .. code-block:: pycon3

        >>> la = LogicArray("1010")
        >>> la[0]  # is indexable
        Logic('0')

        >>> la[1:]  # is slice-able
        LogicArray('10', Range(1, 'downto', 0))

        >>> Logic("0") in la  # is a collection
        True

        >>> list(la)  # is an iterable
        [Logic('1'), Logic('0'), Logic('1'), Logic('0')]

    When setting an element or slice, the *value* is first constructed into a
    :class:`Logic`.

    .. code-block:: pycon3

        >>> la = LogicArray("1010")
        >>> la[3] = "Z"
        >>> la[3]
        Logic('Z')

        >>> la[2:] = ["X", True, 0]
        >>> la
        LogicArray('ZX10', Range(3, 'downto', 0))

        >>> la[:] = 0b0101
        >>> la
        LogicArray('0101', Range(3, 'downto', 0))

    :class:`LogicArray`\ s can be converted into their :class:`str` or :class:`int` literal values using casts.

    .. code-block:: pycon3

        >>> la = LogicArray("1010")
        >>> str(la)
        '1010'
        >>> int(la)
        10

    .. warning::
        The :class:`int` cast assumes the value is entirely ``0`` or ``1`` and will raise an exception otherwise.

    The :meth:`to_unsigned`, :meth:`to_signed`, and :meth:`to_bytes` methods can be used to convert
    the value into an unsigned or signed integer, or bytes, respectively.

    .. code-block:: pycon3

        >>> la.to_unsigned()
        10

        >>> la.to_signed()
        -6

        >>> la.to_bytes(byteorder="big")
        b'\n'

    .. warning::
        These operations assume the value is entirely ``0`` or ``1`` and will raise an exception otherwise.

    You can also convert :class:`LogicArray`\ s to hexadecimal or binary strings using
    the built-ins :func:`hex:` and :func:`bin`, respectively.

    .. code-block:: pycon3

        >>> la = LogicArray("01111010")
        >>> hex(la)
        '0x7a'
        >>> bin(la)
        '0b1111010'

    .. warning::
        Using :func:`hex` or :func:`bin` first turns the LogicArray into an :class:`int`.
        This means the exact length of the LogicArray is lost.
        It also means that these expressions will raise an exception if the value is not entirely ``0`` or ``1``.

    :class:`LogicArray`\ s also support element-wise logical operations: ``&``, ``|``,
    ``^``, and ``~``.

    .. code-block:: pycon3

        >>> def big_mux(a: LogicArray, b: LogicArray, sel: Logic) -> LogicArray:
        ...     s = LogicArray([sel] * len(a))
        ...     return (a & ~s) | (b & s)

        >>> la = LogicArray("0110")
        >>> p = LogicArray("1110")
        >>> sel = Logic("1")  # choose second option
        >>> big_mux(la, p, sel)
        LogicArray('1110', Range(3, 'downto', 0))

    Args:
        value: Initial value for the LogicArray.
        range: The indexing scheme of the LogicArray.

    Raises:
        TypeError: When invalid argument types are used.
        ValueError: When *value* will not fit in a LogicArray of the given *range*.
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

    def __init__(
        self,
        value: Union[int, str, Iterable[LogicConstructibleT]],
        range: Union[Range, int, None] = None,
    ) -> None:
        self._value_as_array = None
        self._value_as_int = None
        self._value_as_str = None

        if isinstance(range, int):
            range = Range(range - 1, "downto", 0)
        elif range is not None and not isinstance(range, Range):
            raise TypeError(
                f"Expected Range or int for parameter 'range', not {type(range).__qualname__}"
            )

        if isinstance(value, str):
            if not (set(value) <= _str_literals):
                raise ValueError("Invalid str literal")
            self._value_as_str = value.upper()
            if range is not None:
                if len(value) != len(range):
                    raise ValueError(
                        f"Value of length {len(self._value_as_str)} will not fit in {range}"
                    )
                self._range = range
            else:
                self._range = Range(len(self._value_as_str) - 1, "downto", 0)
        elif isinstance(value, int):
            if range is None:
                raise TypeError("Missing required arguments: 'range'")

            # Convert to unsigned if signed assuming two's complement.
            limit = 1 << (len(range) - 1)
            if value < -limit or limit <= value:
                raise ValueError(
                    f"{value!r} will not fit in a LogicArray with bounds: {range!r}."
                )
            value %= 2 * limit

            self._value_as_int = value
            self._range = range
        else:
            self._value_as_array = [Logic(v) for v in value]
            if range is not None:
                if len(self._value_as_array) != len(range):
                    raise ValueError(
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

    def _get_int(
        self,
        resolve: "ResolveX | Literal['error'] | Literal['zeros'] | Literal['ones'] | Literal['random'] | None",
    ) -> int:
        if self._value_as_int is None:
            # May convert list to str before converting to int.
            value_as_str = self._get_str()

            # always resolve L and H to 0 and 1
            value_as_str = value_as_str.translate(_resolve_lh_table)

            try:
                self._value_as_int = int(value_as_str, 2)
            except ValueError:
                # value needs resolving
                if resolve is None:
                    resolve = RESOLVE_X

                # resolve remaining
                resolve_table = _resolve_tables[resolve]
                value_as_str = value_as_str.translate(resolve_table)
                return int(value_as_str, 2)

        return self._value_as_int

    @classmethod
    def from_unsigned(
        cls,
        value: int,
        range: Union[Range, int],
    ) -> "LogicArray":
        """Construct a :class:`LogicArray` from an :class:`int` with unsigned representation.

        The :class:`int` is treated as an arbitrary-length bit vector with unsigned representation where the left-most bit is the most significant bit.
        This bit vector is then constructed into a :class:`LogicArray`.

        Args:
            value: The integer to convert.
            range: Indexing scheme for the LogicArray.

        Returns:
            A :class:`LogicArray` equivalent to the *value*.

        Raises:
            TypeError: When invalid argument types are used.
            ValueError: When a :class:`LogicArray` of the given *range* can't hold the *value*, or *value* is negative.
        """
        if value < 0:
            raise ValueError("Expected unsigned integer, got negative value.")
        return LogicArray(value, range)

    @classmethod
    def from_signed(
        cls,
        value: int,
        range: Union[Range, int],
    ) -> "LogicArray":
        """Construct a :class:`LogicArray` from an :class:`int` with two's complement representation.

        The :class:`int` is treated as an arbitrary-length bit vector with two's complement representation where the left-most bit is the most significant bit.
        This bit vector is then constructed into a :class:`LogicArray`.

        Args:
            value: The integer to convert.
            range: Indexing scheme for the LogicArray.

        Returns:
            A :class:`LogicArray` equivalent to the *value*.

        Raises:
            TypeError: When invalid argument types are used.
            ValueError: When a :class:`LogicArray` of the given *range* can't hold the *value*.
        """
        return LogicArray(value, range)

    @classmethod
    def from_bytes(
        cls,
        value: Union[bytes, bytearray],
        range: Union[Range, int, None] = None,
        *,
        byteorder: "Literal['big'] | Literal['little']",
    ) -> "LogicArray":
        """Construct a :class:`LogicArray` from :class:`bytes`.

        The :class:`bytes` is first converted to an unsigned integer using *byteorder*-endian representation,
        then is converted to a :class:`LogicArray` as in :meth:`from_unsigned`.

        Args:
            value: The bytes to convert.
            range: Indexing scheme for the LogicArray.
            byteorder: The endianness used to construct the intermediate integer, either ``"big"`` or ``"little"``.

        Returns:
            A :class:`LogicArray` equivalent to the *value*.

        Raises:
            ValueError: When a :class:`LogicArray` of the given *range* can't hold the *value*.
        """
        if range is None:
            range = Range(len(value) * 8 - 1, "downto", 0)
        else:
            if isinstance(range, int):
                range = Range(range - 1, "downto", 0)
            if len(value) * 8 != len(range):
                raise ValueError(
                    f"Value of length {len(value)} will not fit in a LogicArray with bounds: {range!r}"
                )
        value_as_int = int.from_bytes(value, byteorder=byteorder, signed=False)
        return LogicArray(value_as_int, range)

    @classmethod
    def _from_handle(cls, value: str) -> "LogicArray":
        # Used by cocotb.handle classes to make LogicArray from values gotten from the
        # simulator which we expect to be well-formed.
        # Values are required to be uppercase.
        self = cls.__new__(cls)
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
                if other < 0:
                    return self.to_signed() == other
                else:
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

    @property
    @deprecated("`.binstr` property is deprecated. Use `str(value)` instead.")
    def binstr(self) -> str:
        """Convert the value to the :class:`str` literal representation.

        .. deprecated:: 2.0
        """
        return str(self)

    @property
    def is_resolvable(self) -> bool:
        """``True`` if all elements are ``0``, ``1``, ``L``, ``H``."""
        return all(
            bit in (Logic("0"), Logic("1"), Logic("L"), Logic("H")) for bit in self
        )

    @property
    @deprecated("`.integer` property is deprecated. Use `value.to_unsigned()` instead.")
    def integer(self) -> int:
        """Convert the value to an :class:`int` by interpreting it using unsigned representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using unsigned representation.

        Returns:
            An :class:`int` equivalent to the value by interpreting it using unsigned representation.

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

        Returns:
            An :class:`int` equivalent to the value by interpreting it using two's complement representation.

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

        Returns:
            A :class:`bytes` object equivalent to the value.

        .. deprecated:: 2.0
        """
        return self.to_bytes(byteorder="big")

    def to_unsigned(
        self,
        resolve: "ResolveX | Literal['error'] | Literal['zeros'] | Literal['ones'] | Literal['random'] | None" = None,
    ) -> int:
        """Convert the value to an integer by interpreting it using unsigned representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using unsigned representation.

        Args:
            resolve:
                How ``X``, ``Z``, ``U``, ``W``, and ``-`` values should be resolve to ``0`` or ``1`` to allow conversion to an integer.
                See :class:`ResolveX` for details.
                Defaults to the current value of :attr:`~cocotb.types.logic_array.RESOLVE_X`.

        Returns:
            An integer equivalent to the value by interpreting it using unsigned representation.
        """
        if len(self) == 0:
            warnings.warn("Converting a LogicArray of length 0 to integer")
            return 0
        return self._get_int(resolve)

    def to_signed(
        self,
        resolve: "ResolveX | Literal['error'] | Literal['zeros'] | Literal['ones'] | Literal['random'] | None" = None,
    ) -> int:
        """Convert the value to an integer by interpreting it using two's complement representation.

        The :class:`LogicArray` is treated as an arbitrary-length vector of bits
        with the left-most bit being the most significant bit in the integer value.
        The bit vector is then interpreted as an integer using two's complement representation.

        Args:
            resolve:
                How ``X``, ``Z``, ``U``, ``W``, and ``-`` values should be resolve to ``0`` or ``1`` to allow conversion to an integer.
                See :class:`ResolveX` for details.
                Defaults to the current value of :attr:`~cocotb.types.logic_array.RESOLVE_X`.

        Returns:
            An integer equivalent to the value by interpreting it using two's complement representation.
        """
        if len(self) == 0:
            warnings.warn("Converting a LogicArray of length 0 to integer")
            return 0
        value = self._get_int(resolve)
        if value >= (1 << (len(self) - 1)):
            value -= 1 << len(self)
        return value

    def to_bytes(
        self,
        *,
        byteorder: "Literal['big'] | Literal['little']",
    ) -> bytes:
        """Convert the value to bytes.

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
        self, item: slice, value: Union[str, Iterable[LogicConstructibleT], int]
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
            value = cast(Union[str, Iterable[LogicConstructibleT], int], value)
            value_as_logics = LogicArray(value, stop_i - start_i + 1)
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

    def __index__(self) -> int:
        return int(self)

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

    @deprecated(
        "`bool()` casts and using LogicArray in conditional expressions is deprecated. "
        """Use explicit comparisons (e.g. `LogicArray() == "11"`) or `all`/`any` expressions instead."""
    )
    def __bool__(self) -> bool:
        return any(v in (Logic("H"), Logic("1")) for v in self)
