# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import sys
from random import getrandbits
from typing import Dict

if sys.version_info >= (3, 12):
    from typing import Literal, TypeAlias  # noqa: F401  # used in type strings

ResolverLiteral: "TypeAlias" = "Literal['weak', 'zeros', 'ones', 'random']"


_ord_0 = ord("0")


class random_resolve_table(Dict[int, int]):
    def __init__(self) -> None:
        self[ord("0")] = ord("0")
        self[ord("1")] = ord("1")
        self[ord("L")] = ord("0")
        self[ord("H")] = ord("1")

    def __missing__(self, _: str) -> int:
        return getrandbits(1) + _ord_0


resolvers = {
    "weak": str.maketrans("LHW", "01X"),
    "zeros": str.maketrans("LHUXZW-", "0100000"),
    "ones": str.maketrans("LHUXZW-", "0111111"),
    "random": random_resolve_table(),
}


def resolve_str(value: str, resolver: ResolverLiteral) -> str:
    try:
        resolve_table = resolvers[resolver]
    except KeyError:
        raise ValueError(f"Invalid resolver {resolver!r}")
    return value.translate(resolve_table)
