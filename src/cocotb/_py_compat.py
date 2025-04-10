# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Backports and compatibility shims for newer python features.

These are for internal use - users should use a third party library like `six`
if they want to use these shims in their own code
"""

import sys
from contextlib import AbstractContextManager
from typing import TypeVar, Union, overload

__all__ = (
    "cached_property",
    "insertion_ordered_dict",
    "nullcontext",
)

T = TypeVar("T")

if sys.version_info >= (3, 9):

    class _NullContextBase(AbstractContextManager[T, None]): ...
else:
    from typing import Generic

    class _NullContextBase(AbstractContextManager, Generic[T]): ...


# backport of Python 3.7's contextlib.nullcontext
class nullcontext(_NullContextBase[T]):
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
    from typing import Any, Callable, Generic, Type, TypeVar, Union, overload

    T_co = TypeVar("T_co", covariant=True)

    class cached_property(Generic[T_co]):
        def __init__(self, method: Callable[..., T_co]) -> None:
            self._method = method
            update_wrapper(self, method)  # type: ignore[arg-type]

        @overload
        def __get__(
            self, instance: None, owner: Union[Type[Any], None] = None
        ) -> "cached_property[T_co]": ...

        @overload
        def __get__(
            self, instance: object, owner: Union[Type[Any], None] = None
        ) -> T_co: ...

        def __get__(
            self,
            instance: Union[object, None],
            owner: Union[Type[Any], None] = None,
        ) -> Union["cached_property[T_co]", T_co]:
            if instance is None:
                return self
            res = self._method(instance)
            instance.__dict__[self._method.__name__] = res
            return res
