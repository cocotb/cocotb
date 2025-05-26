# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import warnings
from typing import Any

from cocotb._base_triggers import Event, Lock, NullTrigger, Trigger
from cocotb._extended_awaitables import (
    ClockCycles,
    Combine,
    First,
    SimTimeoutError,
    Waitable,
    with_timeout,
)
from cocotb._gpi_triggers import (
    Edge,
    FallingEdge,
    GPITrigger,
    NextTimeStep,
    ReadOnly,
    ReadWrite,
    RisingEdge,
    Timer,
    ValueChange,
    current_gpi_trigger,
)

__all__ = (
    "ClockCycles",
    "Combine",
    "Edge",
    "Event",
    "FallingEdge",
    "First",
    "GPITrigger",
    "Lock",
    "NextTimeStep",
    "NullTrigger",
    "ReadOnly",
    "ReadWrite",
    "RisingEdge",
    "SimTimeoutError",
    "Timer",
    "Trigger",
    "ValueChange",
    "Waitable",
    "current_gpi_trigger",
    "with_timeout",
)


def __getattr__(name: str) -> Any:
    if name == "Join":
        warnings.warn(
            "Join has been moved to `cocotb.task`.",
            DeprecationWarning,
            stacklevel=2,
        )
        from cocotb.task import Join

        return Join
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
