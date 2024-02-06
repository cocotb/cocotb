# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from abc import ABC, abstractmethod
from typing import Generic, Iterable, Iterator, Optional, TypeVar, Union, overload

T = TypeVar("T")
Self = TypeVar("Self")


from .range import Range  # noqa: E402 F401


class ArrayLike(ABC, Generic[T]):
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
        """Set a new indexing scheme on the array. Must be the same size."""

    def __len__(self) -> int:
        return len(self.range)

    @abstractmethod
    def __iter__(self) -> Iterator[T]:
        ...

    @abstractmethod
    def __reversed__(self) -> Iterator[T]:
        ...

    def __contains__(self, item: object) -> bool:
        for v in self:
            if v == item:
                return True
        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented
        if len(self) != len(other):
            return False
        return all(a == b for a, b in zip(self, other))

    @overload
    def __getitem__(self, item: int) -> T:
        ...

    @overload
    def __getitem__(self: Self, item: slice) -> Self:
        ...

    @abstractmethod
    def __getitem__(self: Self, item: Union[int, slice]) -> Union[T, Self]:
        ...

    @overload
    def __setitem__(self, item: int, value: T) -> None:
        ...

    @overload
    def __setitem__(self, item: slice, value: Iterable[T]) -> None:
        ...

    @abstractmethod
    def __setitem__(
        self, item: Union[int, slice], value: Union[T, Iterable[T]]
    ) -> None:
        ...

    def index(
        self,
        value: T,
        start: Optional[int] = None,
        stop: Optional[int] = None,
    ) -> int:
        """
        Return index of first occurrence of *value*.

        Raises :exc:`IndexError` if the value is not found.
        Search only within *start* and *stop* if given.
        """
        if start is None:
            start = self.left
        if stop is None:
            stop = self.right
        for i in Range(start, self.direction, stop):
            if self[i] == value:
                return i
        raise IndexError(f"{value!r} not in array")

    def count(self, value: T) -> int:
        """Return number of occurrences of *value*."""
        count: int = 0
        for v in self:
            if v == value:
                count += 1
        return 0


from .array import Array  # noqa: E402 F401
from .logic import Logic  # noqa: E402 F401
from .logic_array import LogicArray  # noqa: E402 F401
