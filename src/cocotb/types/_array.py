# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from typing import Iterable, Iterator, List, TypeVar, Union, cast, overload

from cocotb.types._abstract_array import AbstractMutableArray
from cocotb.types._range import Range

T = TypeVar("T")


class Array(AbstractMutableArray[T]):
    r"""Fixed-size, arbitrarily-indexed, homogeneous collection type.

    Arrays are similar to, but different from Python :class:`list`\ s.
    An array can store values of any type or values of multiple types at a time, just like a :class:`!list`.
    Array constructor values can be any Iterable.

    .. code-block:: pycon3

        >>> Array([1, False, "example", None])
        Array([1, False, 'example', None], Range(0, 'to', 3))

        >>> Array("Hello!")
        Array(['H', 'e', 'l', 'l', 'o', '!'], Range(0, 'to', 5))

    Unlike :class:`!list`\ s, an array's size cannot change.
    This means they do not support methods like :meth:`~list.append` or :meth:`~list.insert`.

    The indexes of an Array can start or end at any integer value, they are not limited to 0-based indexing.
    Indexing schemes are selected using :class:`Range` objects.
    If *range* is not given, the range ``Range(0, "to", len(value)-1)`` is used.
    If an :class:`int` is passed for *range*, the range ``Range(0, "to", range-1)`` is used.

    .. code-block:: pycon3

        >>> a = Array([0, 1, 2, 3], Range(-1, "downto", -4))
        >>> a[-1]
        0
        >>> a[-4]
        3

    Arrays can also have 0 length using "null" :class:`Range`\ s.

    .. code-block:: pycon3

        >>> Array([], Range(1, "to", 0))  # 1 to 0 is a null Range
        Array([], Range(1, 'to', 0))

    Indexing and slicing is very similar to :class:`!list`\ s, but it uses the indexing scheme specified with the *range*.
    Unlike :class:`!list`, slicing uses an inclusive right bound, which is common in HDLs.
    But like :class:`!list`, if a start or stop index is not specified in the slice, it is inferred as the start or end of the array.
    Slicing an Array returns a new :class:`~cocotb.types.Array` object, whose bounds are the slice indexes.

    .. code-block:: pycon3

        >>> a = Array("1234abcd")
        >>> a[7]
        'd'
        >>> a[2:5]
        Array(['3', '4', 'a', 'b'], Range(2, 'to', 5))
        >>> a[2:5] = reversed(a[2:5])
        >>> "".join(a)
        '12ba43cd'

        >>> b = Array("1234", Range(0, -3))
        >>> b[-2]
        '3'
        >>> b[-1:]
        Array(['2', '3', '4'], Range(-1, 'downto', -3))
        >>> b[:] = reversed(b)
        >>> b
        Array(['4', '3', '2', '1'], Range(0, 'downto', -3))

    .. warning::
        Arrays behave differently in certain situations than Python's built-in sequence types (:class:`list`, :class:`tuple`, etc.).

        - Arrays are not necessarily 0-based and slices use inclusive right bounds,
          so many functions that work on Python sequences by index (like :mod:`bisect`) may not work on arrays.
        - Slice indexes must be specified in the same direction as the array and do not support specifying a "step".
        - When setting a slice, the new value must be an iterable of the same size as the slice.
        - Negative indexes are *not* treated as an offset from the end of the array, but are treated literally.

    Arrays are equal to other arrays of the same length with the same values (structural equality).
    Bounds do not matter for equality.

    .. code-block:: pycon3

        >>> a = Array([1, 1, 2, 3, 5], Range(4, "downto", 0))
        >>> b = Array([1, 1, 2, 3, 5], Range(-2, "to", 2))
        >>> a == b
        True

    You can change the bounds of an array by setting the :attr:`range` to a new value.
    The new bounds must be the same length of the array.

    .. code-block:: pycon3

        >>> a = Array("1234")
        >>> a.range
        Range(0, 'to', 3)
        >>> a.range = Range(3, "downto", 0)
        >>> a.range
        Range(3, 'downto', 0)

    Arrays support many of the methods and semantics defined by :class:`collections.abc.Sequence`.

    .. code-block:: pycon3

        >>> a = Array("stuff", Range(2, "downto", -2))
        >>> len(a)
        5
        >>> "t" in a
        True
        >>> a.index("u")
        0
        >>> for c in a:
        ...     print(c)
        s
        t
        u
        f
        f

    Args:
        value: Initial value for the Array.
        range: The indexing scheme of the Array.

    Raises:
        ValueError: When argument values cannot be used to construct an Array.
        TypeError: When invalid argument types are used.
    """

    def __init__(
        self, value: Iterable[T], range: Union[Range, int, None] = None
    ) -> None:
        self._value = list(value)
        if range is None:
            self._range = Range(0, "to", len(self._value) - 1)
        else:
            if isinstance(range, int):
                self._range = Range(0, "to", range - 1)
            elif isinstance(range, Range):
                self._range = range
            else:
                raise TypeError(
                    f"Expected Range or int for parameter 'range', not {type(range).__qualname__}"
                )

            if len(self._value) != len(self._range):
                raise ValueError(
                    f"Value of length {len(self._value)!r} does not fit in {self._range!r}"
                )

    @classmethod
    def _from_handle(cls, value: List[T], range: Range) -> "Array[T]":
        self = cls.__new__(cls)
        self._value = value
        self._range = range
        return self

    @property
    def range(self) -> Range:
        """:class:`Range` of the indexes of the array."""
        return self._range

    @range.setter
    def range(self, new_range: Range) -> None:
        """Sets a new indexing scheme on the array, must be the same size"""
        if not isinstance(new_range, Range):
            raise TypeError("range argument must be of type 'Range'")
        if len(new_range) != len(self):
            raise ValueError(
                f"{new_range!r} not the same length as old range ({self._range!r})."
            )
        self._range = new_range

    def __iter__(self) -> Iterator[T]:
        return iter(self._value)

    def __reversed__(self) -> Iterator[T]:
        return reversed(self._value)

    def __contains__(self, item: object) -> bool:
        return item in self._value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Array):
            return self._value == other._value
        elif isinstance(other, list):
            return self._value == other
        elif isinstance(other, tuple):
            return tuple(self._value) == other
        else:
            return NotImplemented

    @overload
    def __getitem__(self, item: int) -> T: ...

    @overload
    def __getitem__(self, item: slice) -> "Array[T]": ...

    def __getitem__(self, item: Union[int, slice]) -> Union[T, "Array[T]"]:
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
            return Array(value=value, range=range)
        raise TypeError(f"indexes must be ints or slices, not {type(item).__name__}")

    @overload
    def __setitem__(self, item: int, value: T) -> None: ...

    @overload
    def __setitem__(self, item: slice, value: Iterable[T]) -> None: ...

    def __setitem__(
        self, item: Union[int, slice], value: Union[T, Iterable[T]]
    ) -> None:
        if isinstance(item, int):
            idx = self._translate_index(item)
            self._value[idx] = cast("T", value)
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
            value = list(cast("Iterable[T]", value))
            if len(value) != (stop_i - start_i + 1):
                raise ValueError(
                    f"value of length {len(value)!r} will not fit in slice [{start}:{stop}]"
                )
            self._value[start_i : stop_i + 1] = value
        else:
            raise TypeError(
                f"indexes must be ints or slices, not {type(item).__name__}"
            )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._value!r}, {self._range!r})"

    def _translate_index(self, item: int) -> int:
        try:
            return self._range.index(item)
        except ValueError:
            raise IndexError(f"index {item} out of range") from None
