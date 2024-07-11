# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""Utility functions for dealing with simulation time."""

import math
from decimal import Decimal
from fractions import Fraction
from functools import lru_cache
from typing import (
    Any,
    Union,
    overload,
)

from cocotb import simulator


def _get_simulator_precision() -> int:
    # cache and replace this function
    precision = simulator.get_precision()
    global _get_simulator_precision
    _get_simulator_precision = precision.__int__
    return _get_simulator_precision()


# Simulator helper functions
def get_sim_time(units: str = "step") -> int:
    """Retrieve the simulation time from the simulator.

    Args:
        units: String specifying the units of the result
            (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``'step'`` will return the raw simulation time.

            .. versionchanged:: 2.0
                Passing ``None`` as the *units* argument was removed, use ``'step'`` instead.

    Raises:
        ValueError: If *units* is not a valid unit (see Args section).

    Returns:
        The simulation time in the specified units.

    .. versionchanged:: 1.6.0
        Support ``'step'`` as the the *units* argument to mean "simulator time step".
    """
    timeh, timel = simulator.get_sim_time()

    result = timeh << 32 | timel

    if units != "step":
        result = get_time_from_sim_steps(result, units)

    return result


@overload
def _ldexp10(frac: int, exp: int) -> int: ...


@overload
def _ldexp10(frac: Union[float, Fraction], exp: int) -> float: ...


@overload
def _ldexp10(frac: Decimal, exp: int) -> Decimal: ...


def _ldexp10(frac: Union[float, Fraction, Decimal], exp: int) -> Any:
    """Like :func:`math.ldexp`, but base 10."""
    # using * or / separately prevents rounding errors if `frac` is a
    # high-precision type
    if exp > 0:
        return frac * (10**exp)
    else:
        return frac / (10**-exp)


def get_time_from_sim_steps(steps: int, units: str) -> int:
    """Calculate simulation time in the specified *units* from the *steps* based
    on the simulator precision.

    Args:
        steps: Number of simulation steps.
        units: String specifying the units of the result
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Raises:
        ValueError: If *units* is not a valid unit (see Args section).

    Returns:
        The simulation time in the specified units.
    """
    return _ldexp10(steps, _get_simulator_precision() - _get_log_time_scale(units))


def get_sim_steps(
    time: Union[float, Fraction, Decimal],
    units: str = "step",
    *,
    round_mode: str = "error",
) -> int:
    """Calculates the number of simulation time steps for a given amount of *time*.

    When *round_mode* is ``"error"``, a :exc:`ValueError` is thrown if the value cannot
    be accurately represented in terms of simulator time steps.
    When *round_mode* is ``"round"``, ``"ceil"``, or ``"floor"``, the corresponding
    rounding function from the standard library will be used to round to a simulator
    time step.

    Args:
        time: The value to convert to simulation time steps.
        units: String specifying the units of the result
            (one of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).
            ``'step'`` means *time* is already in simulation time steps.
        round_mode: String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

    Returns:
        The number of simulation time steps.

    Raises:
        ValueError: if the value cannot be represented accurately in terms of simulator
            time steps when *round_mode* is ``"error"``.

    .. versionchanged:: 1.5
        Support ``'step'`` as the *units* argument to mean "simulator time step".

    .. versionchanged:: 1.6
        Support rounding modes.
    """
    result: Union[float, Fraction, Decimal]
    if units != "step":
        result = _ldexp10(time, _get_log_time_scale(units) - _get_simulator_precision())
    else:
        result = time

    if round_mode == "error":
        result_rounded = math.floor(result)
        if result_rounded != result:
            precision = _get_simulator_precision()
            raise ValueError(
                f"Unable to accurately represent {time}({units}) with the simulator precision of 1e{precision}"
            )
    elif round_mode == "ceil":
        result_rounded = math.ceil(result)
    elif round_mode == "round":
        result_rounded = round(result)
    elif round_mode == "floor":
        result_rounded = math.floor(result)
    else:
        raise ValueError(f"Invalid round_mode specifier: {round_mode}")

    return result_rounded


@lru_cache(maxsize=None)
def _get_log_time_scale(units: str) -> int:
    """Retrieves the ``log10()`` of the scale factor for a given time unit.

    Args:
        units: String specifying the units
            (one of ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``).

    Raises:
        ValueError: If *units* is not a valid unit (see Args section).

    Returns:
        The ``log10()`` of the scale factor for the time unit.
    """
    scale = {"fs": -15, "ps": -12, "ns": -9, "us": -6, "ms": -3, "sec": 0}

    units_lwr = units.lower()
    if units_lwr not in scale:
        raise ValueError(f"Invalid unit ({units}) provided")
    else:
        return scale[units_lwr]
