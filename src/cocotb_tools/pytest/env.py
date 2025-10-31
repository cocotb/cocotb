# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Handling environment variables in friendly way."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

TRUE: tuple[str, ...] = ("1", "yes", "y", "on", "true", "enable")
"""List of expected values for environment variable to be evaluated as True."""

FALSE: tuple[str, ...] = ("0", "no", "n", "off", "false", "disable")
"""List of expected values for environment variable to be evaluated as False."""


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


def as_bool(name: str, default: bool = False) -> bool:
    """Convert value of environment variable to Python boolean type.

    Function is case-insensitive.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        True if environment variable is ``1``, ``yes``, ``y``, ``on``, ``true`` or ``enable``.
        False if environment variable is ``0``, ``no``, ``n``, ``off``, ``false`` or ``disable``.
        Default value if environment variable was not set or it is empty.

    Raises:
        :py:exc:`ValueError` for unexpected value from environment variable.
    """
    envvar: str = as_str(name)  # Keep original case for ValueError
    value: str = envvar.lower()

    if not value:
        return default

    if value in TRUE:
        return True

    if value in FALSE:
        return False

    raise ValueError(
        f"Unexpected value '{envvar}' for environment variable: {name}. "
        f"Expecting one of {(*TRUE,)} or {(*FALSE,)}"
    )


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
