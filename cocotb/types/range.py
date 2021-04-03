from typing import Any, Iterator, overload
from collections.abc import Sequence
from cocotb._py_compat import cached_property, cache


class Range(Sequence):
    r"""
    Variant of :class:`range` with inclusive right bound.

    In Python, :class:`range` and :class:`slice` have a non-inclusive right bound.
    In both Verilog and VHDL, ranges and arrays have an inclusive right bound.
    This type mimic's Python's :class:`range` type, but implements HDL-like inclusive right bounds.
    Also supports :attr:`left`, :attr:`right`, and :attr:`length` attributes as seen in VHDL.

    .. code-block:: python3

        >>> r = Range(-2, 3)
        >>> r.left, r.right, r.length
        (-2, 3, 6)

        >>> s = Range(8, 'downto', 1)
        >>> s.left, s.right, s.length
        (8, 1, 8)

    :meth:`from_range` and :meth:`to_range` can be used to convert from and to :class:`range`.

    .. code-block:: python3

        >>> r = Range(-2, 3)
        >>> r.to_range()
        range(-2, 4)

    Supports "null" ranges as seen in VHDL.
    "null" ranges occur when a left bound cannot reach a right bound with the given direction.
    They have a length of 0, but the left, right, and direction values remain as given.

    .. code-block:: python3

        >>> r = Range(1, 'to', 0)  # no way to count from 1 'to' 0
        >>> r.left, r.direction, r.right
        (1, 'to', 0)
        >>> r.length
        0

    .. note::
        This is only possible when specifying the direction.

    Ranges also support all the features of :class:`range` including, but not limited to:

    - ``value in range`` to see if a value is in the range,
    - ``range.index(value)`` to see what position in the range the value is,
    - ``len(range)`` which is equivalent to :attr:`length`.

    The typical use case of this type is in conjunction with :class:`~cocotb.types.Array`.

    Args:
        left: leftmost bound of range
        direction: 'to' if values are ascending or 'downto' if descending
        right: rightmost bound of range (inclusive)
    """

    __slots__ = ("_range", "__dict__")  # __dict__ necessary for cached_property

    @overload
    def __init__(self, left: int, right: int):
        pass  # pragma: no cover

    @overload
    def __init__(self, *, left: int, right: int):
        pass  # pragma: no cover

    @overload
    def __init__(self, left: int, direction: str, right: int):
        pass  # pragma: no cover

    def __init__(self, left, direction=None, right=None):
        if direction is not None and right is None:
            right, direction = direction, None
        if direction is None:
            step = 1 if left < right else -1
        else:
            step = self._translate_direction(direction)
        self._range = range(left, right + step, step)

    @staticmethod
    @cache
    def _translate_direction(direction) -> int:
        direction = direction.lower()
        if direction == "to":
            return 1
        elif direction == "downto":
            return -1
        else:
            raise ValueError("direction must be 'to' or 'downto'")

    @classmethod
    def from_range(cls, rng: range) -> "Range":
        """Converts :class:`range` to :class:`Range`."""
        if rng.step not in (1, -1):
            raise ValueError("step must be 1 or -1")
        obj = cls.__new__(cls)
        obj._range = rng
        return obj

    def to_range(self) -> range:
        """Convert :class:`Range` to :class:`range`."""
        return self._range

    @cached_property
    def left(self) -> int:
        """Leftmost value in a range."""
        return self._range.start

    @cached_property
    def direction(self) -> str:
        """``'to'`` if values are meant to be ascending, ``'downto'`` otherwise."""
        return "to" if self._range.step == 1 else "downto"

    @cached_property
    def right(self) -> int:
        """Rightmost value in a range."""
        return self._range.stop - self._range.step

    @cached_property
    def length(self) -> int:
        """Length of range."""
        return len(self._range)

    def __len__(self) -> int:
        return self.length

    @overload
    def __getitem__(self, item: int) -> int:
        pass  # pragma: no cover

    @overload
    def __getitem__(self, item: slice) -> "Range":
        pass  # pragma: no cover

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._range[item]
        elif isinstance(item, slice):
            return type(self).from_range(self._range[item])
        raise TypeError(
            "indices must be integers or slices, not {}".format(type(item).__name__)
        )

    def __contains__(self, item: Any) -> bool:
        return item in self._range

    def __iter__(self) -> Iterator[int]:
        return iter(self._range)

    def __reversed__(self) -> Iterator[int]:
        return reversed(self._range)

    def __eq__(self, other: Any) -> bool:
        if type(self) is not type(other):
            return NotImplemented
        return self._range == other._range

    def __hash__(self) -> int:
        return hash(self._range)

    def index(self, item: Any) -> int:
        return self._range.index(item)

    def count(self, item: Any) -> int:
        return self._range.count(item)

    def __repr__(self) -> str:
        return "{}({!r}, {!r}, {!r})".format(
            type(self).__name__, self.left, self.direction, self.right
        )
