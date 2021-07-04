# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import typing

T = typing.TypeVar("T")


class Range(typing.Sequence[int]):
    r"""
    Variant of :class:`range` with inclusive right bound.

    In Python, :class:`range` and :class:`slice` have a non-inclusive right bound.
    In both Verilog and VHDL, ranges and arrays have an inclusive right bound.
    This type mimics Python's :class:`range` type, but implements HDL-like inclusive right bounds,
    using the names :attr:`left` and :attr:`right` as replacements for ``start`` and ``stop`` to
    match VHDL.
    Range directionality can be specified using ``'to'`` or ``'downto'`` between the
    left and right bounds.
    Not specifying directionality will cause the directionality to be inferred.

    .. code-block:: python3

        >>> r = Range(-2, 3)
        >>> r.left, r.right, len(r)
        (-2, 3, 6)

        >>> s = Range(8, 'downto', 1)
        >>> s.left, s.right, len(s)
        (8, 1, 8)

    :meth:`from_range` and :meth:`to_range` can be used to convert from and to :class:`range`.

    .. code-block:: python3

        >>> r = Range(-2, 3)
        >>> r.to_range()
        range(-2, 4)

    :class:`Range` supports "null" ranges as seen in VHDL.
    "null" ranges occur when a left bound cannot reach a right bound with the given direction.
    They have a length of 0, but the :attr:`left`, :attr:`right`, and :attr:`direction` values remain as given.

    .. code-block:: python3

        >>> r = Range(1, 'to', 0)  # no way to count from 1 'to' 0
        >>> r.left, r.direction, r.right
        (1, 'to', 0)
        >>> len(r)
        0

    .. note::
        This is only possible when specifying the direction.

    Ranges also support all the features of :class:`range` including, but not limited to:

    - ``value in range`` to see if a value is in the range,
    - ``range.index(value)`` to see what position in the range the value is,

    The typical use case of this type is in conjunction with :class:`~cocotb.types.Array`.

    Args:
        left: leftmost bound of range
        direction: ``'to'`` if values are ascending, ``'downto'`` if descending
        right: rightmost bound of range (inclusive)
    """

    __slots__ = ("_range",)

    @typing.overload
    def __init__(self, left: int, direction: int) -> None:
        pass  # pragma: no cover

    @typing.overload
    def __init__(self, left: int, direction: str, right: int) -> None:
        pass  # pragma: no cover

    @typing.overload
    def __init__(self, left: int, *, right: int) -> None:
        pass  # pragma: no cover

    def __init__(
        self,
        left: int,
        direction: typing.Union[int, str, None] = None,
        right: typing.Union[int, None] = None,
    ) -> None:
        start = left
        stop: int
        step: int
        if isinstance(direction, int) and right is None:
            step = _guess_step(left, direction)
            stop = direction + step
        elif direction is None and isinstance(right, int):
            step = _guess_step(left, right)
            stop = right + step
        elif isinstance(direction, str) and isinstance(right, int):
            step = _direction_to_step(direction)
            stop = right + step
        else:
            raise TypeError("invalid arguments")
        self._range = range(start, stop, step)

    @classmethod
    def from_range(cls, range: range) -> "Range":
        """Convert :class:`range` to :class:`Range`."""
        return cls(
            left=range.start,
            direction=_step_to_direction(range.step),
            right=(range.stop - range.step),
        )

    def to_range(self) -> range:
        """Convert :class:`Range` to :class:`range`."""
        return self._range

    @property
    def left(self) -> int:
        """Leftmost value in a range."""
        return self._range.start

    @property
    def direction(self) -> str:
        """``'to'`` if values are meant to be ascending, ``'downto'`` otherwise."""
        return _step_to_direction(self._range.step)

    @property
    def right(self) -> int:
        """Rightmost value in a range."""
        return self._range.stop - self._range.step

    def __len__(self) -> int:
        return len(self._range)

    @typing.overload
    def __getitem__(self, item: int) -> int:
        pass  # pragma: no cover

    @typing.overload
    def __getitem__(self, item: slice) -> "Range":
        pass  # pragma: no cover

    def __getitem__(self, item: typing.Union[int, slice]) -> typing.Union[int, "Range"]:
        if isinstance(item, int):
            return self._range[item]
        elif isinstance(item, slice):
            return type(self).from_range(self._range[item])
        raise TypeError(
            "indices must be integers or slices, not {}".format(type(item).__name__)
        )

    def __contains__(self, item: object) -> bool:
        return item in self._range

    def __iter__(self) -> typing.Iterator[int]:
        return iter(self._range)

    def __reversed__(self) -> typing.Iterator[int]:
        return reversed(self._range)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, type(self)):
            return self._range == other._range
        return NotImplemented  # must not be in a type narrowing context to be ignored properly

    def __hash__(self) -> int:
        return hash(self._range)

    def count(self, item: int) -> int:
        return self._range.count(item)

    def __repr__(self) -> str:
        return "{}({!r}, {!r}, {!r})".format(
            type(self).__qualname__, self.left, self.direction, self.right
        )


def _guess_step(left: int, right: int) -> int:
    if left <= right:
        return 1
    return -1


def _direction_to_step(direction: str) -> int:
    direction = direction.lower()
    if direction == "to":
        return 1
    elif direction == "downto":
        return -1
    raise ValueError("direction must be 'to' or 'downto'")


def _step_to_direction(step: int) -> str:
    if step == 1:
        return "to"
    elif step == -1:
        return "downto"
    raise ValueError("step must be 1 or -1")
