# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from random import Random
from typing import Literal, Protocol, cast

if sys.version_info >= (3, 10):
    from typing import TypeAlias


ResolverLiteral: TypeAlias = Literal["error", "weak", "zeros", "ones", "random"]

# global resolver, default to "weak" for backwards compatibility of is_resolvable/resolve.
_resolve_method: ResolverLiteral = "weak"


def get_default_resolve_method() -> ResolverLiteral:
    """Returns the global default resolver method."""
    return _resolve_method


def set_default_resolve_method(method: ResolverLiteral) -> None:
    """Sets the global default resolver method."""
    global _resolve_method
    _resolve_method = method


def resolve(value: str, resolver: ResolverLiteral | None = None) -> str:
    """Resolves a value using the specified resolver method.

    ``None`` resolves using the global default resolver method.
    """
    if resolver is None:
        resolver = get_default_resolve_method()

    if resolver == "random":
        return "".join(map(_rnd_table.__getitem__, value))

    try:
        table = _resolve_tables[resolver]
    except KeyError:
        raise ValueError(
            f"Invalid resolver: {resolver!r}. {_VALID_RESOLVERS_ERR_MSG}"
        ) from None

    return value.translate(table)


class IsResolvable(Protocol):
    def __bool__(self) -> bool: ...
    def __call__(self, resolver: ResolverLiteral | None = None) -> bool: ...


class IsResolvableLogic:
    def __init__(self, value: str) -> None:
        self._value = value

    def _is_resolvable(self, resolver: ResolverLiteral) -> bool:
        if resolver not in _VALID_RESOLVERS:
            raise ValueError(
                f"Invalid resolver: {resolver!r}. {_VALID_RESOLVERS_ERR_MSG}"
            ) from None
        # Works for 1 character strings.
        return self._value in _resolvable_values_table[resolver]

    def __bool__(self) -> bool:
        return self._is_resolvable(get_default_resolve_method())

    def __call__(self, resolver: ResolverLiteral | None = None) -> bool:
        if resolver is None:
            resolver = get_default_resolve_method()
        return self._is_resolvable(resolver)


class IsResolvableLogicArray(IsResolvableLogic):
    def _is_resolvable(self, resolver: ResolverLiteral) -> bool:
        if resolver not in _VALID_RESOLVERS:
            raise ValueError(
                f"Invalid resolver: {resolver!r}. {_VALID_RESOLVERS_ERR_MSG}"
            ) from None
        # Works for N character strings. Confirmed faster than `all(c in table for c in self._value)`.
        return frozenset(self._value).issubset(_resolvable_values_table[resolver])


class _IsResolvableBool:
    def __bool__(self) -> bool:
        return True

    def __call__(self, resolver: ResolverLiteral | None = None) -> bool:
        return True


# There only needs to be one instance since Bit/BitArray are always resolvable.
is_resolvable_bool = _IsResolvableBool()


_randomResolveRng = Random()

_01lookup = ("0", "1")


class _random_resolve_table(dict[str, str]):
    def __init__(self) -> None:
        self["0"] = "0"
        self["1"] = "1"
        self["L"] = "0"
        self["H"] = "1"

    def __missing__(self, _: str) -> str:
        return _01lookup[_randomResolveRng.getrandbits(1)]


_rnd_table = _random_resolve_table()


_resolve_tables: dict[str, dict[int, int]] = {
    "error": {},
    "weak": str.maketrans("LHW", "01X"),
    "zeros": str.maketrans("LHUXZW-", "0100000"),
    "ones": str.maketrans("LHUXZW-", "0111111"),
}

_resolvable_values_table = {
    "error": frozenset("01"),
    "weak": frozenset("01LH"),
    "zeros": frozenset("01LHUXZW-"),
    "ones": frozenset("01LHUXZW-"),
    "random": frozenset("01LHUXZW-"),
}

_VALID_RESOLVERS = ("error", "weak", "zeros", "ones", "random")
_VALID_RESOLVERS_ERR_MSG = (
    "Valid values are 'error', 'weak', 'zeros', 'ones', or 'random'"
)


def _init() -> None:
    resolver = os.getenv("COCOTB_RESOLVE_X", "").lower()

    # no resolver, leave as default
    if not resolver:
        return

    # backwards compatibility
    if resolver == "value_error":
        resolver = "error"

    # set resolve method
    if resolver not in _VALID_RESOLVERS:
        raise ValueError(
            f"Invalid COCOTB_RESOLVE_X value: {resolver!r}. {_VALID_RESOLVERS_ERR_MSG}"
        ) from None
    set_default_resolve_method(cast("ResolverLiteral", resolver))
