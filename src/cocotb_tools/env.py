# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Handling environment variables in consistent and unified way."""

from __future__ import annotations

import os
import shlex
from collections.abc import Iterable
from pathlib import Path

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


def as_str(name: str, default: str | None = None, strip: bool = True) -> str:
    """Convert value of environment variable to Python string type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.
        strip: Strip value from leading and trailing whitespace characters.

    Returns:
        Stripped string of environment variable.
    """
    value: str = os.environ.get(name, "")

    if strip:
        value = value.strip()

    return value or default or ""


def as_bool(name: str, default: bool | None = None) -> bool:
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
        return default or False

    if value in TRUE:
        return True

    if value in FALSE:
        return False

    raise ValueError(
        f"Unexpected value {envvar!r} for environment variable: {name!r}. "
        f"Expecting one of {(*TRUE,)} or {(*FALSE,)}"
    )


def as_list(
    name: str, default: Iterable[str] | None = None, separator: str = ","
) -> list[str]:
    """Convert value of environment variable to Python list of strings type.

    Values by default are comma ``,`` separated.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.
        separator: Used separator between values.

    Returns:
        List of striped and non-empty strings.
    """
    items: list[str] = list(filter(None, map(str.strip, as_str(name).split(separator))))

    return list(items or default or ())


def as_int(name: str, default: int | None = None) -> int:
    """Convert value of environment variable to Python integer type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        Integer. If value was not set, it will return zero (0).
    """
    return int(as_str(name) or default or 0)


def as_path(name: str, default: Path | str | None = None) -> Path:
    """Convert value of environment variable to Python path type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        Resolved path. If path was not set, it will return current working directory.
    """
    return Path(as_str(name) or default or "").resolve()


def as_paths(
    name: str, default: Iterable[Path | str] | Path | str | None = None
) -> list[Path]:
    """Convert value of environment variable to list of Python path types.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        List of resolved paths.
    """
    if isinstance(default, (Path, str)):
        default = (default,)

    return [Path(path).resolve() for path in as_list(name) or default or ()]


def as_args(name: str, default: str | None = None) -> list[str]:
    """Convert value of environment variable to list of arguments respecting shell syntax.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        List of arguments split based on shell syntax.
    """
    return shlex.split(as_str(name) or default or "")
