# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Handling environment variables in a consistent and unified way."""

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


def get_str(name: str, default: str | None = None) -> str:
    """Convert value of environment variable to Python string type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        Stripped string of environment variable.
    """
    return os.environ.get(name, "").strip() or default or ""


def get_bool(name: str, default: bool | None = None) -> bool:
    """Convert value of environment variable to Python boolean type.

    Function is case-insensitive.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        :data:`True` if the environment variable is ``1``, ``yes``, ``y``, ``on``, ``true`` or ``enable``.
        :data:`False` if the environment variable is ``0``, ``no``, ``n``, ``off``, ``false`` or ``disable``.
        Default value if environment variable was not set or is empty.

    Raises:
        :exc:`ValueError` in case of an unexpected value.
    """
    value = get_str(name)  # Keep original case for ValueError

    if not value:
        return default or False

    try:
        return as_bool(value)
    except ValueError:
        raise ValueError(
            f"Unexpected value {value!r} for environment variable: {name!r}. "
            f"Expecting one of {(*TRUE,)} or {(*FALSE,)} (case-insensitive)"
        ) from None


def as_bool(value: str) -> bool:
    """Convert envvar string value to Python boolean type.

    Args:
        value: String value to convert. Case-insensitive.

    Returns:
        :data:`True` if the value is ``1``, ``yes``, ``y``, ``on``, ``true`` or ``enable``.
        :data:`False` if the value is ``0``, ``no``, ``n``, ``off``, ``false`` or ``disable``.
    """
    value = value.lower()
    if value in TRUE:
        return True
    if value in FALSE:
        return False
    raise ValueError(
        f"Unexpected value: {value!r}. Expecting one of {(*TRUE,)} or {(*FALSE,)} (case-insensitive)"
    )


def get_list(
    name: str, default: Iterable[str] | None = None, separator: str = ","
) -> list[str]:
    """Convert value of environment variable to Python list of strings type.

    Values by default are comma (``,``) separated.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.
        separator: Used separator between values.

    Returns:
        List of stripped and non-empty strings.
    """
    items: list[str] = list(
        filter(None, map(str.strip, get_str(name).split(separator)))
    )

    return list(items or default or ())


def get_int(name: str, default: int | None = None) -> int:
    """Convert value of environment variable to Python integer type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        Integer. If value was not set, it will return zero (0).
    """
    return int(get_str(name) or default or 0)


def get_path(name: str, default: Path | str | None = None) -> Path:
    """Convert value of environment variable to Python path type.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        The resolved path. If not set, the current working directory will be returned.
    """
    return Path(get_str(name) or default or "").resolve()


def get_args(name: str, default: str | None = None) -> list[str]:
    """Convert value of environment variable to list of arguments respecting shell syntax.

    Args:
        name: Name of environment variable.
        default: Default value of environment variable.

    Returns:
        List of arguments split based on shell syntax.
    """
    return shlex.split(get_str(name) or default or "")
