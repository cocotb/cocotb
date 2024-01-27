# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from abc import ABC, abstractmethod
from typing import Any, Generic, Iterable, Iterator, Optional, TypeVar, Union, overload

try:
    from typing import Protocol
except ImportError:
    try:
        from typing_extensions import Protocol
    except ImportError:
        Protocol = ABC

T = TypeVar("T")
Self = TypeVar("Self")


class Concatable(Protocol, Generic[T]):
    def __concat__(self: Self, other: Self) -> Self:
        return NotImplemented

    def __rconcat__(self: Self, other: Self) -> Self:
        return NotImplemented


ConcatableT = TypeVar("ConcatableT", bound=Concatable[Any])


def concat(a: ConcatableT, b: ConcatableT) -> ConcatableT:
    """
    Create a new array that is the concatenation of one array with another.

    Uses the :meth:`__concat__` or :meth:`__rconcat__` special methods to dispatch to a particular implementation,
    exactly like other binary operations in Python.

    Raises:
        TypeError: when the arguments do not support concatenation in the given order.
    """
    MISSING = object()
    type_a = type(a)
    type_b = type(b)
    a_concat = getattr(type_a, "__concat__", MISSING)
    a_rconcat = getattr(type_a, "__rconcat__", MISSING)
    b_rconcat = getattr(type_b, "__rconcat__", MISSING)

    if type_a is not type_b and issubclass(type_b, type_a) and a_rconcat != b_rconcat:
        # 'b' is a subclass of 'a' with a more specific implementation of 'concat(a, b)'
        call_order = [(b, b_rconcat, a), (a, a_concat, b)]
    elif type_a is not type_b:
        # normal call order
        call_order = [(a, a_concat, b), (b, b_rconcat, a)]
    else:
        # types are the same, we expect implementation of 'concat(a, b)' to be in 'a.__concat__'
        call_order = [(a, a_concat, b)]

    for lhs, method, rhs in call_order:
        if method is MISSING:
            continue
        res = method(lhs, rhs)
        if res is not NotImplemented:
            return res

    raise TypeError(
        f"cannot concatenate {type_a.__qualname__!r} with {type_b.__qualname__!r}"
    )


from .range import Range  # noqa: E402 F401


class ArrayLike(Concatable[T], Protocol, Generic[T]):
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
