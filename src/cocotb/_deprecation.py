# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import functools
import sys
import warnings
from typing import Callable, TypeVar

AnyCallableT = TypeVar("AnyCallableT", bound=Callable[..., object])


if sys.version_info >= (3, 13):
    from warnings import deprecated

else:

    def deprecated(
        msg: str, *, category: type[Warning] = DeprecationWarning, stacklevel: int = 1
    ) -> Callable[[AnyCallableT], AnyCallableT]:
        """Emits a DeprecationWarning when the decorated function is called.

        This decorator works on normal functions, methods, and properties.
        Usage on properties requires the ``@property`` decorator to appear outside the
        ``@deprecated`` decorator.
        Concrete classes can be deprecated by decorating their ``__init__`` or ``__new__``
        method.

        Args:
            msg: the deprecation message
            category: the warning class to use
            stacklevel: the stack level for the warning
        """

        def decorator(f: AnyCallableT) -> AnyCallableT:
            @functools.wraps(f)
            def wrapper(*args: object, **kwargs: object) -> object:
                warnings.warn(msg, category=category, stacklevel=1 + stacklevel)
                return f(*args, **kwargs)

            return wrapper  # type: ignore[return-value]  # type checkers get confused about this

        return decorator
