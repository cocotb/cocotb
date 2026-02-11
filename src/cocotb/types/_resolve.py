# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from functools import cache
from random import Random
from typing import Callable, Final, Literal, cast

from cocotb_tools import _env

if sys.version_info >= (3, 10):
    from typing import TypeAlias

ResolverLiteral: TypeAlias = Literal["weak", "zeros", "ones", "random"]


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

_VALID_RESOLVERS = ("error", "weak", "zeros", "ones", "random")
_VALID_RESOLVERS_ERR_MSG = (
    "Valid values are 'error', 'weak', 'zeros', 'ones', or 'random'"
)


@cache
def get_str_resolver(resolver: ResolverLiteral) -> Callable[[str], str]:
    if resolver not in _VALID_RESOLVERS:
        raise ValueError(f"Invalid resolver: {resolver!r}. {_VALID_RESOLVERS_ERR_MSG}")

    if resolver == "random":
        # Can't use str.translate for random resolving as it assumes that the mapping
        # will not change over the course of the call.
        def resolve_func(value: str) -> str:
            return "".join(map(_rnd_table.__getitem__, value))

    else:
        resolve_table = _resolve_tables[resolver]

        def resolve_func(value: str) -> str:
            return value.translate(resolve_table)

    return resolve_func


def _init() -> Callable[[str], str] | None:
    resolver = _env.as_str("COCOTB_RESOLVE_X").lower()

    # no resolver
    if not resolver:
        return None

    # backwards compatibility
    if resolver == "value_error":
        resolver = "error"

    # get resolver
    try:
        return get_str_resolver(cast("ResolverLiteral", resolver))
    except ValueError:
        raise ValueError(
            f"Invalid COCOTB_RESOLVE_X value: {resolver!r}. {_VALID_RESOLVERS_ERR_MSG}"
        ) from None


RESOLVE_X: Final = _init()
