# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Collection of small handy utilities."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def to_list(value: Any) -> list[Any]:
    """Convert any provided value to list.

    Args:
        value: Any kidn of value that will be converted to list.

    Returns:
        Converted value to list.
    """
    if isinstance(value, list):
        return value

    if isinstance(value, Iterable) and not isinstance(value, str):
        return list(value)

    return [value]
