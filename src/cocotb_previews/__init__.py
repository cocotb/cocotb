# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Enable or disable previews of upcoming cocotb behavior."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value


if sys.version_info >= (3, 11):
    from typing import Self


class Feature(StrEnum):
    """Preview features that can be enabled.

    .. versionadded:: 2.1

    .. versionchanged:: 2.2
        Moved from ``cocotb.preview`` to ``cocotb_previews``.
    """

    def __new__(cls, value: str, doc: str | None = None) -> Self:
        # Inline DocStrEnum so we don't have a dependency cycle on cocotb
        self = str.__new__(cls, value)
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self

    XFAIL_IN_RESULTS = (
        "xfail_in_results",
        "Use the ``XFAIL`` status in the terminal results summary and the ``skipped`` XML element in the generated JUnit XML file for xfailed tests",
    )
    STRICT_RESOLVE = (
        "strict_resolve",
        "`Logic.resolve()` and `LogicArray.resolve()` return `Bit` or 0/1-only `LogicArray`, respectively",
    )
    HANDLE_LEN_IS_SUBELEMENTS = (
        "handle_len_is_subelements",
        "Make ``len()`` on packed objects return the number of elements in the outermost dimension instead of the number of bits",
    )
    RUNNER_TEMP_BUILD_DIR = (
        "runner_temp_build_dir",
        "Use a randomly-named temporary build directory prefixed with `sim_build_` as the default build directory in the Python runner",
    )


_feature_strs = {feature.value for feature in Feature}

_TRUE = ("1", "yes", "y", "on", "true", "enable")
_FALSE = ("0", "no", "n", "off", "false", "disable")

_enabled_features: set[Feature] = set()


def enable(feature: Feature) -> None:
    """Enable a preview feature.

    Args:
        feature: Preview feature to enable.

    .. versionadded:: 2.1
    """
    _enabled_features.add(feature)


def disable(feature: Feature) -> None:
    """Disable a preview feature.

    Args:
        feature: Preview feature to disable.

    .. versionadded:: 2.1
    """
    _enabled_features.discard(feature)


def is_enabled(feature: Feature) -> bool:
    """Check if a preview feature is enabled.

    Args:
        feature: Preview feature to check.

    Returns:
        :data:`True` if the feature is enabled, otherwise :data:`False`.

    .. versionadded:: 2.1
    """
    return feature in _enabled_features


def _parse_features(features: str) -> Iterable[Feature]:
    for value in features.split(","):
        feature = value.strip()
        if not feature:
            continue
        if feature not in _feature_strs:
            raise ValueError(f"Unknown preview feature: {feature!r}")
        yield Feature(feature)


def _init() -> None:
    features = os.getenv("COCOTB_PREVIEW")
    if not features:
        return

    value = features.lower()
    if value in _TRUE:
        _enabled_features.update(Feature)
    elif value not in _FALSE:
        # Not a bool flag, so parse as a list of features.
        _enabled_features.update(_parse_features(features))


_init()
