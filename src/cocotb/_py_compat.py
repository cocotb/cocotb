# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Backports and compatibility shims for newer python features.

These are for internal use - users should use a third party library like `six`
if they want to use these shims in their own code
"""

from __future__ import annotations

import sys
from contextlib import AbstractContextManager
from typing import TypeVar, overload

__all__ = (
    "StrEnum",
    "nullcontext",
)

T = TypeVar("T")


# backport of Python 3.7's contextlib.nullcontext
class nullcontext(AbstractContextManager[T, None]):
    """Context manager that does no additional processing.
    Used as a stand-in for a normal context manager, when a particular
    block of code is only sometimes used with a normal context manager:

    cm = optional_cm if condition else nullcontext()
    with cm:
        # Perform operation, using optional_cm if condition is True
    """

    enter_result: T

    @overload
    def __init__(self: nullcontext[None], enter_result: None = None) -> None: ...

    @overload
    def __init__(self: nullcontext[T], enter_result: T) -> None: ...

    def __init__(self: nullcontext[T | None], enter_result: T | None = None) -> None:
        self.enter_result = enter_result

    def __enter__(self) -> T:
        return self.enter_result

    def __exit__(self, *excinfo: object) -> None:
        pass


if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value
