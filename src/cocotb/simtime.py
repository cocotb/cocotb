# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Tools for dealing with simulated time."""

import warnings
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from math import ceil, floor
from typing import Union, cast, overload

from cocotb import simulator
from cocotb._py_compat import Literal, TypeAlias
from cocotb._typing import RoundMode, TimeUnit

__all__ = (
    "convert",
    "get_sim_time",
    "time_precision",
)


Steps: TypeAlias = Literal["step"]
TimeUnitWithoutSteps: TypeAlias = Literal["fs", "ps", "ns", "us", "ms", "sec"]


@overload
def convert(
    value: Union[float, Fraction, Decimal],
    unit: TimeUnit,
    *,
    to: Steps,
    round_mode: RoundMode = "error",
) -> int: ...


@overload
def convert(
    value: Union[float, Fraction, Decimal],
    unit: TimeUnit,
    *,
    to: TimeUnitWithoutSteps,
    round_mode: RoundMode = "error",
) -> float: ...


def convert(
    value: Union[float, Decimal, Fraction],
    unit: TimeUnit,
    *,
    to: TimeUnit,
    round_mode: RoundMode = "error",
) -> float:
    """Convert time values from one unit to another unit.

    Args:
        value: The time value.

        unit: The unit of *value* (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

        to: The unit to convert *value* to (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

        round_mode:
            How to handle non-integral step values (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

            When *round_mode* is ``"error"``, a :exc:`ValueError` is thrown if the value cannot
            be accurately represented in terms of simulator time steps.
            When *round_mode* is ``"round"``, ``"ceil"``, or ``"floor"``, the corresponding
            rounding function from the standard library will be used to round to a simulator
            time step.

    Returns:
        The value scaled by the difference in units.

    .. versionadded:: 2.0
    """
    if unit == "step":
        steps = cast("int", value)
    else:
        steps = _get_sim_steps(value, unit, round_mode=round_mode)
    if to == "step":
        return steps
    else:
        return _get_time_from_sim_steps(steps, to)


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

    .. versionchanged:: 2.0
        Moved from :mod:`cocotb.utils` to :mod:`cocotb.simtime`.
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
    return _get_time_from_sim_steps(steps, unit) if unit != "step" else steps


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


def _get_time_from_sim_steps(
    steps: int,
    unit: TimeUnit,
) -> float:
    if unit == "step":
        return steps
    return _ldexp10(steps, time_precision - _get_log_time_scale(unit))


def _get_sim_steps(
    time: Union[float, Fraction, Decimal],
    unit: TimeUnit = "step",
    *,
    round_mode: RoundMode = "error",
) -> int:
    result: Union[float, Fraction, Decimal]
    if unit != "step":
        result = _ldexp10(time, _get_log_time_scale(unit) - time_precision)
    else:
        result = time

    if round_mode == "error":
        result_rounded = floor(result)
        if result_rounded != result:
            raise ValueError(
                f"Unable to accurately represent {time}({unit}) with the simulator precision of 1e{time_precision}"
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


@lru_cache(maxsize=None)
def _get_log_time_scale(unit: TimeUnitWithoutSteps) -> int:
    """Retrieve the ``log10()`` of the scale factor for a given time unit.

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


time_precision: int = _get_log_time_scale("fs")
"""The precision of time in the current simulation.

The value is seconds in powers of tens,
i.e. ``-15`` is ``10**-15`` seconds or 1 femtosecond.

.. versionadded:: 2.0
"""


def _init() -> None:
    global time_precision
    time_precision = simulator.get_precision()
