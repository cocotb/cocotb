# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Plugin markers."""

from __future__ import annotations

from inspect import Parameter, signature
from typing import Callable

from pytest import Config, MarkDecorator, mark

from cocotb.simtime import TimeUnit


def cocotb(
    *test_module: str,
    timeout: tuple[float, TimeUnit] | None = None,
    **kwargs: object,
) -> MarkDecorator:
    """Mark coroutine function as cocotb test and normal function as cocotb runner.

    Args:
        test_module:
            Name of Python module with cocotb tests to be loaded by cocotb runner.

        timeout:
            Simulation time duration before the test is forced to fail with a :exc:`~cocotb.triggers.SimTimeoutError`.
            A tuple of the timeout value and unit.
            Accepts any unit that :class:`~cocotb.triggers.Timer` does.

        kwargs:
            Additional named arguments passed to :py:class:`cocotb_tools.pytest.hdl.HDL` instance.
    """
    return mark.cocotb(
        *test_module,
        timeout=timeout,
        **kwargs,
    )


def marker_description(marker: Callable[..., MarkDecorator]) -> str:
    """Get pretty formatted description of marker.

    Args:
        marker: Definition of marker for pytest.

    Returns:
        Pretty formatted description of provided marker.
    """
    args: list[str] = []

    for name, parameter in signature(cocotb).parameters.items():
        arg: str = ""

        if parameter.kind == Parameter.VAR_POSITIONAL:
            arg = f"*{name}"

        elif parameter.kind == Parameter.VAR_KEYWORD:
            arg = f"**{name}"

        else:
            arg = name

        if parameter.annotation != Parameter.empty:
            arg += f": {parameter.annotation}"

        if parameter.default != Parameter.empty:
            arg += f" = {parameter.default}"

        args.append(arg)

    return f"{marker.__name__}({', '.join(args)}):\n    {marker.__doc__}".rstrip()


def register_markers(config: Config) -> None:
    """Register plugin markers.

    Args:
        config: Pytest configuration object.
    """
    config.addinivalue_line("markers", marker_description(cocotb))
