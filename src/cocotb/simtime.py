# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Utility functions for dealing with simulation time."""

import warnings
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from math import ceil, floor
from typing import Union, overload

from cocotb import simulator
from cocotb._py_compat import Literal, TypeAlias
from cocotb._typing import RoundMode, TimeUnit

__all__ = (
    "get_sim_steps",
    "get_sim_time",
    "get_time_from_sim_steps",
)


def _get_simulator_precision() -> int:
    # cache and replace this function
    precision = simulator.get_precision()
    global _get_simulator_precision
    _get_simulator_precision = precision.__int__
    return _get_simulator_precision()


# Simulator helper functions
def get_sim_time(unit: TimeUnit = "step", *, units: None = None) -> float:
    """Retrieve the simulation time from the simulator.

    Args:
        unit: String specifying the unit of the result
            (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``'step'`` will return the raw simulation time.

            .. versionchanged:: 2.0
                Passing ``None`` as the *unit* argument was removed, use ``'step'`` instead.

            .. versionchanged:: 2.0
                Renamed from ``units``.

    Raises:
        ValueError: If *unit* is not a valid unit.

    Returns:
        The simulation time in the specified unit.

    .. versionchanged:: 1.6
        Support ``'step'`` as the the *unit* argument to mean "simulator time step".
    """
    if units is not None:
        warnings.warn(
            "The 'units' argument has been renamed to 'unit'.",
            DeprecationWarning,
            stacklevel=2,
        )
        unit = units
    timeh, timel = simulator.get_sim_time()
    steps = timeh << 32 | timel
    return get_time_from_sim_steps(steps, unit) if unit != "step" else steps


@overload
def _ldexp10(frac: float, exp: int) -> float: ...


@overload
def _ldexp10(frac: Fraction, exp: int) -> Fraction: ...


@overload
def _ldexp10(frac: Decimal, exp: int) -> Decimal: ...


def _ldexp10(
    frac: Union[float, Fraction, Decimal], exp: int
) -> Union[float, Fraction, Decimal]:
    """Like :func:`math.ldexp`, but base 10."""
    # using * or / separately prevents rounding errors if `frac` is a
    # high-precision type
    if exp > 0:
        return frac * (10**exp)
    else:
        return frac / (10**-exp)


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
    if unit == "step":
        return steps
    return _ldexp10(steps, _get_simulator_precision() - _get_log_time_scale(unit))


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
    result: Union[float, Fraction, Decimal]
    if unit != "step":
        result = _ldexp10(time, _get_log_time_scale(unit) - _get_simulator_precision())
    else:
        result = time

    if round_mode == "error":
        result_rounded = floor(result)
        if result_rounded != result:
            precision = _get_simulator_precision()
            raise ValueError(
                f"Unable to accurately represent {time}({unit}) with the simulator precision of 1e{precision}"
            )
    elif round_mode == "ceil":
        result_rounded = ceil(result)
    elif round_mode == "round":
        result_rounded = round(result)
    elif round_mode == "floor":
        result_rounded = floor(result)
    else:
        raise ValueError(f"Invalid round_mode specifier: {round_mode}")

    return result_rounded


TimeUnitWithoutSteps: TypeAlias = Literal["fs", "ps", "ns", "us", "ms", "sec"]


@lru_cache(maxsize=None)
def _get_log_time_scale(unit: TimeUnitWithoutSteps) -> int:
    """Retrieves the ``log10()`` of the scale factor for a given time unit.

    Args:
        unit: String specifying the unit
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

            .. versionchanged:: 2.0
                Renamed from ``units``.

    Raises:
        ValueError: If *unit* is not a valid unit.

    Returns:
        The ``log10()`` of the scale factor for the time unit.
    """
    scale = {"fs": -15, "ps": -12, "ns": -9, "us": -6, "ms": -3, "sec": 0}

    unit_lwr = unit.lower()
    if unit_lwr not in scale:
        raise ValueError(f"Invalid unit ({unit}) provided")
    else:
        return scale[unit_lwr]
