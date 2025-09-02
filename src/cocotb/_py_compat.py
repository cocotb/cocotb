# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Backports and compatibility shims for newer python features.

These are for internal use - users should use a third party library like `six`
if they want to use these shims in their own code
"""

import sys
from abc import ABC
from contextlib import AbstractContextManager
from typing import TypeVar, Union, overload

__all__ = (
    "AbstractContextManager",
    "Final",
    "Literal",
    "ParamSpec",
    "Protocol",
    "Self",
    "StrEnum",
    "TypeAlias",
    "cached_property",
    "insertion_ordered_dict",
    "nullcontext",
)

T = TypeVar("T")

if sys.version_info < (3, 9):
    from typing import Generic

    T_co = TypeVar("T_co", covariant=True)
    ExitT_co = TypeVar("ExitT_co", covariant=True)

    class AbstractContextManager(AbstractContextManager, Generic[T_co, ExitT_co]): ...


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
    def __init__(self: "nullcontext[None]", enter_result: None = None) -> None: ...

    @overload
    def __init__(self: "nullcontext[T]", enter_result: T) -> None: ...

    def __init__(
        self: "nullcontext[Union[T, None]]", enter_result: Union[T, None] = None
    ) -> None:
        self.enter_result = enter_result

    def __enter__(self) -> T:
        return self.enter_result

    def __exit__(self, *excinfo: object) -> None:
        pass


# On python 3.7 onwards, `dict` is guaranteed to preserve insertion order.
# Since `OrderedDict` is a little slower that `dict`, we prefer the latter
# when possible.
if sys.version_info[:2] >= (3, 7):  # noqa: UP036 | bug in ruff
    insertion_ordered_dict = dict
else:
    import collections

    insertion_ordered_dict = collections.OrderedDict


# simple, but less than optimal backport of Python 3.8's cached_property
if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    from functools import update_wrapper

    class cached_property:
        def __init__(self, method):
            self._method = method
            update_wrapper(self, method)

        def __get__(self, instance, owner=None):
            if instance is None:
                return self
            res = self._method(instance)
            instance.__dict__[self._method.__name__] = res
            return res


if sys.version_info >= (3, 8):
    from typing import Final, Literal, Protocol
else:
    from typing import Any

    class FakeGetItemType:
        def __class_getitem__(self, a: object) -> Any:
            return Any

    Final = FakeGetItemType
    Literal = FakeGetItemType
    Protocol = ABC


if sys.version_info >= (3, 10):
    from typing import ParamSpec, TypeAlias
else:
    from typing import Any

    TypeAlias = Any

    class FakeParamSpecType:
        def __init__(self, name: str) -> None: ...

        def kwargs(self) -> Any:
            return Any

        def args(self) -> Any:
            return Any

    ParamSpec = FakeParamSpecType


if sys.version_info >= (3, 11):
    from typing import Self
else:
    Self = ""


if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value
