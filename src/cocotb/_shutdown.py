# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import Callable

_callbacks: list[Callable[[], None]] = []
"""List of callbacks to be called when cocotb shuts down."""


def register(cb: Callable[[], None]) -> None:
    """Register a callback to be called when cocotb shuts down."""
    _callbacks.append(cb)


def _shutdown() -> None:
    """Call all registered shutdown callbacks."""
    while _callbacks:
        cb = _callbacks.pop(0)
        cb()


def _init() -> None:
    from cocotb import simulator  # noqa: PLC0415

    simulator.set_sim_event_callback(_shutdown)
