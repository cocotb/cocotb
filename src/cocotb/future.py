# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Enable or disable experimental features or breaking changes."""

from __future__ import annotations

import os
from collections.abc import Iterable

from cocotb._utils import DocStrEnum
from cocotb_tools import _env


class Future(DocStrEnum):
    """Experimental features or breaking changes that can be enabled.

    .. versionadded:: 2.1
    """

    XFAIL_IN_RESULTS = (
        "xfail_in_results",
        "Use the ``XFAIL`` status in the terminal results summary and the ``skipped`` XML element in the generated JUnit XML file for xfailed tests",
    )


_future_strs = {future.value for future in Future}

_enabled_futures: set[Future] = set()


def enable(future: Future) -> None:
    """Enable a future.

    Args:
        future: Future to enable.

    .. versionadded:: 2.1
    """
    _enabled_futures.add(future)


def disable(future: Future) -> None:
    """Disable a future.

    Args:
        future: Future to disable.

    .. versionadded:: 2.1
    """
    _enabled_futures.discard(future)


def is_enabled(future: Future) -> bool:
    """Check if a future is enabled.

    Args:
        future: Future to check.

    Returns:
        :data:`True` if the future is enabled, otherwise :data:`False`.

    .. versionadded:: 2.1
    """
    return future in _enabled_futures


def _parse_futures(futures: str) -> Iterable[Future]:
    for fut in futures.split(","):
        future = fut.strip()
        if not future:
            continue
        if future not in _future_strs:
            raise ValueError(f"Unknown future: {future!r}")
        yield Future(future)


def _init() -> None:
    futures = os.getenv("COCOTB_FUTURE")
    if not futures:
        return

    try:
        bool_flag = _env.as_bool(futures)
    except ValueError:
        # if not a bool, try parsing as list of futures
        requested_futures = list(_parse_futures(futures))
        _enabled_futures.update(requested_futures)
    else:
        # Is bool flag, if False, skip.
        # If True, enable all futures.
        if not bool_flag:
            return
        _enabled_futures.update(Future)
