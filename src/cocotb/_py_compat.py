# Copyright (c) cocotb contributors
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
Backports and compatibility shims for newer python features.

These are for internal use - users should use a third party library like `six`
if they want to use these shims in their own code
"""

import sys
from contextlib import AbstractContextManager


# backport of Python 3.7's contextlib.nullcontext
class nullcontext(AbstractContextManager):
    """Context manager that does no additional processing.
    Used as a stand-in for a normal context manager, when a particular
    block of code is only sometimes used with a normal context manager:

    cm = optional_cm if condition else nullcontext()
    with cm:
        # Perform operation, using optional_cm if condition is True
    """

    def __init__(self, enter_result=None):
        self.enter_result = enter_result

    def __enter__(self):
        return self.enter_result

    def __exit__(self, *excinfo):
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


# inheriting from (str, Enum) was broken in 3.11 and StrEnum must be used
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        pass
