# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Enable or disable previews of upcoming cocotb behavior."""

from __future__ import annotations

import os
from collections.abc import Iterable

from cocotb._utils import DocStrEnum
from cocotb_tools import _env


class Feature(DocStrEnum):
    """Preview features that can be enabled.

    .. versionadded:: 2.1
    """

    XFAIL_IN_RESULTS = (
        "xfail_in_results",
        "Use the XFAIL status in the terminal results summary for xfailed tests",
    )


_feature_strs = {feature.value for feature in Feature}

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

    try:
        bool_flag = _env.as_bool(features)
    except ValueError:
        # If not a bool, try parsing as a list of features.
        requested_features = list(_parse_features(features))
        _enabled_features.update(requested_features)
    else:
        # If this is a false bool flag, skip. If true, enable all features.
        if not bool_flag:
            return
        _enabled_features.update(Feature)
