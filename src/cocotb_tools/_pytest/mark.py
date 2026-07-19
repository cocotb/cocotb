# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Plugin markers."""

from __future__ import annotations

from inspect import Parameter, signature
from typing import Callable

from pytest import Config, MarkDecorator, mark

from cocotb.simtime import TimeUnit


def cocotb() -> MarkDecorator:
    """Mark test function as a cocotb test/runner.

    .. note::

        Marker is set automatically by plugin on cocotb tests and runners.

    Returns:
        Decorated test function as a cocotb test/runner.
    """
    return mark.cocotb()


def cocotb_timeout(duration: float, unit: TimeUnit) -> MarkDecorator:
    """Mark coroutine function with simulation time duration before the test is forced to fail.

    Example usage:

    .. code:: python

        @pytest.mark.cocotb_timeout(duration=200, unit="ns")
        async def test_dut_feature_with_timeout(dut) -> None:
            # Test DUT feature with timeout configured from cocotb marker
            ...

    Args:
        duration: Simulation time duration before the test is forced to fail.
        unit: Simulation time unit that accepts any unit that :class:`~cocotb.triggers.Timer` does.

    Raises:
        :exc:`~cocotb.triggers.SimTimeoutError`: Test function timeouted.

    Returns:
        Decorated coroutine function with simulation time duration before the test is forced to fail.
    """
    return mark.cocotb_timeout(duration=duration, unit=unit)


def _marker_description(marker: Callable[..., MarkDecorator]) -> str:
    """Get pretty formatted description of marker.

    Args:
        marker: Definition of marker for pytest.

    Returns:
        Pretty formatted description of provided marker.
    """
    args: list[str] = []

    for name, parameter in signature(marker).parameters.items():
        arg: str = ""

        if parameter.kind == Parameter.VAR_KEYWORD:
            arg = f"{name}=..."

        else:
            arg = name

        if parameter.default != Parameter.empty:
            arg += f"={parameter.default}"

        if parameter.kind == Parameter.KEYWORD_ONLY and "*" not in args:
            args.append("*")

        args.append(arg)

        if parameter.kind == Parameter.VAR_POSITIONAL:
            args.append("...")

    description: str = str(marker.__doc__).lstrip().splitlines()[0]

    return f"{marker.__name__}({', '.join(args)}): {description}".rstrip()


def _register_markers(config: Config) -> None:
    """Register plugin markers.

    Args:
        config: Pytest configuration object.
    """
    for marker in (cocotb, cocotb_timeout):
        config.addinivalue_line("markers", _marker_description(marker))
