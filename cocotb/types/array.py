# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from typing import Optional, Any, Iterable, Iterator, overload
from collections.abc import Sequence
from .range import Range
from sys import maxsize


class Array(Sequence):
    r"""
    Fixed-size, arbitrarily-indexed, heterogeneous sequence type.

    Arrays are similar to, but different from Python :class:`list`\ s.
    An array can store values of any type or values of multiple types at a time, just like a :class:`list`.
    Unlike :class:`list`\ s, an array's size cannot change.

    The indexes of an array can start or end at any integer value, they are not limited to 0-based indexing.
    Indexing schemes can be either ascending or descending in value.
    An array's indexes are described using a :class:`~cocotb.types.Range` object.
    Initial values are treated as iterables, which are copied into an internal buffer.

    .. code-block:: python3

        >>> Array("1234")  # the 0-based range `(0, len(value)-1)` is inferred
        Array(['1', '2', '3', '4'], Range(0, 'to', 3))

        >>> Array(range=Range(0, "downto", -3))  # the initial values are `None`
        Array([None, None, None, None], Range(0, 'downto', -3))

        >>> Array([1, True, None, "example"], Range(-2, 1))  # initial value and range lengths must be equal
        Array([1, True, None, 'example'], Range(-2, 'to', 1))

    Arrays also support "null" ranges; "null" arrays have zero length and cannot be indexed.

    .. code-block:: python3

        >>> Array(range=Range(1, "to", 0))
        Array([], Range(1, 'to', 0))

    Indexing and slicing is very similar to :class:`list`\ s, but it uses the indexing scheme specified.
    Slicing, just like the :class:`~cocotb.types.Range` object uses an inclusive right bound,
    which is commonly seen in HDLs.
    Like :class:`list`\ s, if a start or stop index is not specified, it is inferred as the start or end of the array.
    Slicing an array returns a new :class:`~cocotb.types.Array` object, whose bounds are the slice indexes.

    .. code-block:: python3

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
        Arrays behave differently in certain situations than Python's builtin sequence types (:class:`list`, :class:`tuple`, etc.).

        - Arrays are not necessarily 0-based and slices use inclusive right bounds,
          so many functions that work on Python sequences by index (like :mod:`bisect`) may not work on arrays.
        - Slice indexes must be specified in the same direction as the array and do not support specifying a "step".
        - When setting a slice, the new value must be an iterable of the same size as the slice.
        - Negative indexes are *not* treated as an offset from the end of the array, but are treated literally.

    Arrays are equal to other arrays of the same length with the same values (structural equality).
    Bounds do not matter for equality.

    .. code-block:: python3

        >>> a = Array([1, 1, 2, 3, 5], Range(4, "downto", 0))
        >>> b = Array([1, 1, 2, 3, 5], Range(-2, "to", 2))
        >>> a == b
        True

    You can change the bounds of an array by setting the :attr:`range` to a new value.
    The new bounds must be the same length of the array.

    .. code-block:: python3

        >>> a = Array("1234")
        >>> a.range
        Range(0, 'to', 3)
        >>> a.range = Range(3, 'downto', 0)
        >>> a.range
        Range(3, 'downto', 0)

    Arrays support the methods and semantics defined by :class:`collections.abc.Sequence`.

    .. code-block:: python

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
        value: Initial value for the array.
        range: Indexing scheme of the array.

    Raises:
        ValueError: When argument values cannot be used to construct an array.
        TypeError: When invalid argument types are used.
    """

    __slots__ = (
        "_value",
        "_range",
    )

    _value: Sequence
    """
    Private interface for subclasses to access the value as a :class:`~collections.abc.Sequence`

    Subclasses that don't use a Sequence as their main representation should emulate this object,
    or override *all* :class:`~cocotb.types.Array` methods *except*:
        - :attr:`left`
        - :attr:`direction`
        - :attr:`right`
        - :attr:`range`
        - :attr:`__len__`
        - :attr:`_translate_index`
    """

    def __init__(
        self, value: Optional[Iterable[Any]] = None, range: Optional[Range] = None
    ):
        if value is not None and range is None:
            self._value = list(value)
            self._range = Range(0, "to", len(self._value) - 1)
        elif value is not None and range is not None:
            if not isinstance(range, Range):
                raise TypeError("range argument must be of type 'Range'")
            self._value = list(value)
            self._range = range
            if len(self._value) != len(self._range):
                raise ValueError(
                    "init value of length {!r} does not fit in {!r}".format(
                        len(self._value), self._range
                    )
                )
        elif value is None and range is not None:
            if not isinstance(range, Range):
                raise TypeError("range argument must be of type 'Range'")
            self._value = [None] * len(range)
            self._range = range
        else:
            raise TypeError("must pass a value, range, or both")

    @property
    def left(self) -> int:
        """Leftmost index of the array."""
        return self.range.left

    @property
    def direction(self) -> str:
        """``"to"`` if indexes are ascending, ``"downto"`` otherwise."""
        return self.range.direction

    @property
    def right(self) -> int:
        """Rightmost index of the array."""
        return self.range.right

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

    def __len__(self) -> int:
        return len(self.range)

    def __iter__(self) -> Iterator[Any]:
        return iter(self._value)

    def __reversed__(self) -> Iterator[Any]:
        return reversed(self._value)

    def __contains__(self, item: Any) -> bool:
        return item in self._value

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        return self._value == other._value

    @overload
    def __getitem__(self, item: int) -> Any:
        pass  # pragma: no cover

    @overload
    def __getitem__(self, item: slice) -> "Array":
        pass  # pragma: no cover

    def __getitem__(self, item):
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
                    "slice [{}:{}] direction does not match array direction [{}:{}]".format(
                        start, stop, self.left, self.right
                    )
                )
            value = self._value[start_i : stop_i + 1]
            range = Range(start, self.direction, stop)
            return type(self)(value=value, range=range)
        raise TypeError(
            "indexes must be ints or slices, not {}".format(type(item).__name__)
        )

    @overload
    def __setitem__(self, item: int, value: Any) -> None:
        pass  # pragma: no cover

    @overload
    def __setitem__(self, item: slice, value: Iterable[Any]) -> None:
        pass  # pragma: no cover

    def __setitem__(self, item, value):
        if isinstance(item, int):
            idx = self._translate_index(item)
            self._value[idx] = value
        elif isinstance(item, slice):
            start = item.start if item.start is not None else self.left
            stop = item.stop if item.stop is not None else self.right
            if item.step is not None:
                raise IndexError("do not specify step")
            start_i = self._translate_index(start)
            stop_i = self._translate_index(stop)
            if start_i > stop_i:
                raise IndexError(
                    "slice [{}:{}] direction does not match array direction [{}:{}]".format(
                        start, stop, self.left, self.right
                    )
                )
            value = list(value)
            if len(value) != (stop_i - start_i + 1):
                raise ValueError(
                    "value of length {!r} will not fit in slice [{}:{}]".format(
                        len(value), start, stop
                    )
                )
            self._value[start_i : stop_i + 1] = value
        else:
            raise TypeError(
                "indexes must be ints or slices, not {}".format(type(item).__name__)
            )

    def __repr__(self) -> str:
        return "{}({!r}, {!r})".format(type(self).__name__, self._value, self._range)

    def __concat__(self, other: "Array") -> "Array":
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(self._value + other._value)

    def __rconcat__(self, other: "Array") -> "Array":
        if not isinstance(other, type(self)):
            return NotImplemented
        return type(self)(other._value + self._value)

    def index(
        self, value: Any, start: Optional[int] = None, stop: Optional[int] = None
    ) -> int:
        """
        Return index of first occurrence of *value*.

        Raises :exc:`ValueError` if the value is not found.
        Search only within *start* and *stop* if given.
        """
        if start is not None:
            start = self._translate_index(start)
        else:
            start = 0
        if stop is not None:
            stop = self._translate_index(stop)
        else:
            stop = maxsize  # same default value used by Python lists
        idx = self._value.index(value, start, stop)
        return self._range[idx]

    def count(self, value: Any) -> int:
        """Return number of occurrences of *value*."""
        return self._value.count(value)

    def _translate_index(self, item: int) -> int:
        try:
            return self._range.index(item)
        except ValueError:
            raise IndexError(f"index {item} out of range") from None
