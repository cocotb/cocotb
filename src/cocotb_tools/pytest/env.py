# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Handling environment variables in friendly way."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def exists(name: str) -> bool:
    """Check if environment variable was defined.

    Args:
        name: Name of environment variable.

    Returns:
        True if environment variable was defined. Otherwise False.
    """
    return name in os.environ


def as_str(name: str, default: Any = None) -> str:
    """Convert value of environment variable to Python string type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        Striped string of environment variable.
    """
    if default is None:
        default = ""
    elif isinstance(default, str):
        pass
    elif isinstance(default, Iterable):
        default = ",".join(default)
    else:
        default = str(default)

    value: str = os.environ.get(name, default).strip()

    return value if value else default


def as_bool(name: str, default: Any = None) -> bool:
    """Convert value of environment variable to Python boolean type.

    Function is case-insensitive.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        ``True`` if environment variable is ``1``, ``true``, ``yes``, ``y``, ``enable``, ``on``.
        Otherwise ``False``.
    """
    return as_str(name, default).lower() in ("1", "true", "yes", "y", "enable", "on")


def as_list(name: str, default: Any = None) -> list[str]:
    """Convert value of environment variable to Python list of strings type.

    Values are comma ``,`` separated.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        List of striped and non-empty strings.
    """
    return list(filter(None, map(str.strip, as_str(name, default).split(","))))


def as_int(name: str, default: Any = 0) -> int:
    """Convert value of environment variable to Python integer type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        Integer.
    """
    return int(as_str(name, default))


def as_path(name: str, default: Any = None) -> Path:
    """Convert value of environment variable to Python path type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        Path type.
    """
    return Path(as_str(name, default))
