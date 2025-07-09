# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from abc import abstractmethod
from typing import Generic, Iterable, Iterator, Optional, TypeVar, Union, overload

from cocotb.types._range import Range

T_co = TypeVar("T_co", covariant=True)
T = TypeVar("T")


class AbstractArray(Generic[T_co]):
    r"""Abstract base class for non-mutating Array-like collections.

    Arrays are similar to :class:`~collections.abc.Sequence`\ s,
    but their size cannot change after creation and they support arbitrary indexing schemes.

    Abstract methods
    ^^^^^^^^^^^^^^^^

    * :attr:`range`
    * :meth:`!__getitem__`

    Mixin methods
    ^^^^^^^^^^^^^

    * :attr:`left`, :attr:`right`, and :attr:`direction`
    * :meth:`!__len__`
    * :meth:`!__iter__` and :meth:`!__reversed__`
    * :meth:`!__contains__`
    * :meth:`index` and :meth:`count`
    """

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
    @abstractmethod
    def range(self) -> Range:
        """:class:`Range` of the indexes of the array."""

    @range.setter
    @abstractmethod
    def range(self, new_range: Range) -> None:
        """Set a new indexing scheme on the array.

        Must be the same size.
        """

    def __len__(self) -> int:
        return len(self.range)

    def __iter__(self) -> Iterator[T_co]:
        for i in self.range:
            yield self[i]

    def __reversed__(self) -> Iterator[T_co]:
        for i in reversed(self.range):
            yield self[i]

    def __contains__(self, item: object) -> bool:
        return any(v == item for v in self)

    @overload
    def __getitem__(self, item: int) -> T_co: ...

    @overload
    def __getitem__(self, item: slice) -> "AbstractArray[T_co]": ...

    @abstractmethod
    def __getitem__(
        self, item: Union[int, slice]
    ) -> Union[T_co, "AbstractArray[T_co]"]: ...

    def index(
        self,
        value: object,
        start: Optional[int] = None,
        stop: Optional[int] = None,
    ) -> int:
        """Find first occurrence of value.

        Args:
            value: Value to search for.
            start: Index to start search at.
            stop: Index to stop search at.

        Returns:
            Index of first occurrence of *value*.

        Raises:
            ValueError: If the value is not present.
        """
        if start is None:
            start = self.left
        if stop is None:
            stop = self.right
        for i in Range(start, self.direction, stop):
            if self[i] == value:
                return i
        raise IndexError(f"{value!r} not in array")

    def count(self, value: object) -> int:
        """Return number of occurrences of value.

        Args:
            value: Value to search for.

        Returns:
            Number of occurrences of *value*.
        """
        count: int = 0
        for v in self:
            if v == value:
                count += 1
        return count


class AbstractMutableArray(AbstractArray[T]):
    """Abstract base class for mutating Array-like collections.

    See :class:`.AbstractArray` for more details.

    Additional abstract methods:

    * :meth:`!__setitem__`
    """

    @overload
    def __setitem__(self, item: int, value: T) -> None: ...

    @overload
    def __setitem__(self, item: slice, value: Iterable[T]) -> None: ...

    @abstractmethod
    def __setitem__(
        self, item: Union[int, slice], value: Union[T, Iterable[T]]
    ) -> None: ...
