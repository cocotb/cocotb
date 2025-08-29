# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Tools for dealing with simulated time."""

import warnings
from decimal import Decimal
from fractions import Fraction
from typing import Union

from cocotb._typing import RoundMode, TimeUnit
from cocotb.simtime import (
    _get_sim_steps,
    _get_time_from_sim_steps,
    get_sim_time,
)

__all__ = (
    "get_sim_steps",
    "get_sim_time",
    "get_time_from_sim_steps",
)


def get_time_from_sim_steps(
    steps: int,
    unit: Union[TimeUnit, None] = None,
    *,
    units: None = None,
) -> float:
    """Calculate simulation time in the specified *unit* from the *steps* based
    on the simulator precision.

    Args:
        steps: Number of simulation steps.
        unit: String specifying the unit of the result
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

            .. versionchanged:: 2.0
                Renamed from ``units``.

    Raises:
        ValueError: If *unit* is not a valid unit.

    Returns:
        The simulation time in the specified unit.
    """
    if units is not None:
        warnings.warn(
            "The 'units' argument has been renamed to 'unit'.",
            DeprecationWarning,
            stacklevel=2,
        )
        unit = units
    if unit is None:
        raise TypeError("Missing required argument 'unit'")
    return _get_time_from_sim_steps(steps, unit)


def get_sim_steps(
    time: Union[float, Fraction, Decimal],
    unit: TimeUnit = "step",
    *,
    round_mode: RoundMode = "error",
    units: None = None,
) -> int:
    """Calculates the number of simulation time steps for a given amount of *time*.

    When *round_mode* is ``"error"``, a :exc:`ValueError` is thrown if the value cannot
    be accurately represented in terms of simulator time steps.
    When *round_mode* is ``"round"``, ``"ceil"``, or ``"floor"``, the corresponding
    rounding function from the standard library will be used to round to a simulator
    time step.

    Args:
        time: The value to convert to simulation time steps.
        unit: String specifying the unit of the result
            (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``'step'`` means *time* is already in simulation time steps.

            .. versionchanged:: 2.0
                Renamed from ``units``.

        round_mode: String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

    Returns:
        The number of simulation time steps.

    Raises:
        ValueError: if the value cannot be represented accurately in terms of simulator
            time steps when *round_mode* is ``"error"``.

    .. versionchanged:: 1.5
        Support ``'step'`` as the *unit* argument to mean "simulator time step".

    .. versionchanged:: 1.6
        Support rounding modes.
    """
    if units is not None:
        warnings.warn(
            "The 'units' argument has been renamed to 'unit'.",
            DeprecationWarning,
            stacklevel=2,
        )
        unit = units
    return _get_sim_steps(time, unit, round_mode=round_mode)
