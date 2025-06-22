# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os
from functools import lru_cache
from random import getrandbits
from typing import Callable, Dict, Union

from cocotb._py_compat import Final, Literal, TypeAlias

ResolverLiteral: TypeAlias = Literal["weak", "zeros", "ones", "random"]


_ord_0 = ord("0")


class _random_resolve_table(Dict[int, int]):
    def __init__(self) -> None:
        self[ord("0")] = ord("0")
        self[ord("1")] = ord("1")
        self[ord("L")] = ord("0")
        self[ord("H")] = ord("1")

    def __missing__(self, _: str) -> int:
        return getrandbits(1) + _ord_0


_resolve_tables: Dict[str, Dict[int, int]] = {
    "error": {},
    "weak": str.maketrans("LHW", "01X"),
    "zeros": str.maketrans("LHUXZW-", "0100000"),
    "ones": str.maketrans("LHUXZW-", "0111111"),
    "random": _random_resolve_table(),
}

_VALID_RESOLVERS = ("error", "weak", "zeros", "ones", "random")
_VALID_RESOLVERS_ERR_MSG = (
    "Valid values are 'error', 'weak', 'zeros', 'ones', or 'random'"
)


@lru_cache(maxsize=None)
def get_str_resolver(resolver: ResolverLiteral) -> Callable[[str], str]:
    if resolver not in _VALID_RESOLVERS:
        raise ValueError(f"Invalid resolver: {resolver!r}. {_VALID_RESOLVERS_ERR_MSG}")

    resolve_table = _resolve_tables[resolver]

    def resolve_func(value: str) -> str:
        return value.translate(resolve_table)

    return resolve_func


def _init() -> Union[Callable[[str], str], None]:
    _envvar = os.getenv("COCOTB_RESOLVE_X", None)

    # no resolver
    if _envvar is None:
        return None

    # backwards compatibility
    resolver = _envvar.strip().lower()
    if resolver == "value_error":
        resolver = "error"

    # get resolver
    try:
        return get_str_resolver(resolver)
    except ValueError:
        raise ValueError(
            f"Invalid COCOTB_RESOLVE_X value: {_envvar!r}. {_VALID_RESOLVERS_ERR_MSG}"
        ) from None


RESOLVE_X: Final = _init()
