# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Plugin markers."""

from __future__ import annotations

from inspect import Parameter, signature
from typing import Callable

from pytest import Config, MarkDecorator, mark

from cocotb.simtime import TimeUnit
from cocotb_tools.runner import (
    VHDL,
    PathLike,
    VerilatorControlFile,
    Verilog,
)


def cocotb_runner(test_module: str = "", *extra_test_module: str) -> MarkDecorator:
    """Mark test function as cocotb runner.

    Example usage:

    .. code:: python

        import pytest
        from cocotb_tools.pytest.hdl import HDL

        @pytest.fixture(name="sample_module")
        def sample_module_fixture(hdl: HDL) -> HDL:
            # Define HDL design and build it
            hdl.toplevel = "sample_module"
            hdl.sources = [DESIGNS / "sample_module.sv"]

            return hdl

        @pytest.mark.cocotb_runner
        def test_dut(sample_module: HDL) -> None:
            # Run HDL simulator with cocotb tests
            sample_module.test()

    Args:
        test_module:
            Name of Python module with cocotb tests to be loaded by cocotb :py:attr:`~cocotb_tools.pytest.hdl.HDL.runner`.

    Returns:
        Decorated test function as cocotb runner.
    """
    return mark.cocotb_runner(test_module=test_module, *extra_test_module)


def cocotb_test() -> MarkDecorator:
    """Mark coroutine function as cocotb test.

    Example usage:

    .. code:: python

        # NOTE: decorator is not needed if coroutine function starts with the test_ prefix and it uses dut fixture
        async def test_dut_feature(dut) -> None:
            # Test DUT feature
            ...

        @pytest.mark.cocotb_test
        async def non_canonical_test_name(dut) -> None:
            # Test DUT feature but from a test function that doesn't follow with the pytest naming convention
            ...

    Returns:
        Decorated coroutine function as cocotb test.
    """
    return mark.cocotb_test()


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


def cocotb_sources(
    *source: PathLike | Verilog | VHDL | VerilatorControlFile,
) -> MarkDecorator:
    """Add language-agnostic list of source files to build."""
    return mark.cocotb_sources(*source)


def cocotb_defines(**define: object) -> MarkDecorator:
    """Set defines."""
    return mark.cocotb_defines(**define)


def cocotb_parameters(**parameter: object) -> MarkDecorator:
    """Set Verilog/SystemVerilog parameters and VHDL generics."""
    return mark.cocotb_parameters(**parameter)


def cocotb_env(**env: str) -> MarkDecorator:
    """Set environment variables."""
    return mark.cocotb_env(**env)


def cocotb_includes(*include: PathLike) -> MarkDecorator:
    """Add Verilog includes."""
    return mark.cocotb_includes(*include)


def cocotb_plusargs(*plusarg: str) -> MarkDecorator:
    """Add plus arguments for the simulator."""
    return mark.cocotb_plusargs(*plusarg)


def cocotb_timescale(unit: str, precision: str | None = None) -> MarkDecorator:
    """Set time unit and time precision for simulation."""
    return mark.cocotb_timescale(unit=unit, precision=precision)


def cocotb_seed(value: int) -> MarkDecorator:
    """A specific random seed to use."""
    return mark.cocotb_seed(value=value)


def cocotb_build_args(*arg: str | VHDL | Verilog) -> MarkDecorator:
    """Add extra build arguments for the simulator."""
    return mark.cocotb_build_args(*arg)


def cocotb_elab_args(*arg: str) -> MarkDecorator:
    """Add extra elaboration arguments to the simulator."""
    return mark.cocotb_elab_args(*arg)


def cocotb_test_args(*arg: str) -> MarkDecorator:
    """Add extra runtime arguments to the simulator."""
    return mark.cocotb_test_args(*arg)


def cocotb_pre_cmd(*arg: str) -> MarkDecorator:
    """Add extra commands to run before simulation begins. Typically Tcl commands for simulators that support them.."""
    return mark.cocotb_pre_cmd(*arg)


def cocotb_library(name: str) -> MarkDecorator:
    """Set the library name to compile into."""
    return mark.cocotb_library(name=name)


def cocotb_waves(condition: bool = True) -> MarkDecorator:
    """Record signal traces."""
    return mark.cocotb_waves(condition=condition)


def cocotb_verbose(condition: bool = True) -> MarkDecorator:
    """Enable verbose messages."""
    return mark.cocotb_verbose(condition=condition)


def cocotb_always(condition: bool = True) -> MarkDecorator:
    """Always run the build step."""
    return mark.cocotb_always(condition=condition)


def cocotb_clean(condition: bool = True) -> MarkDecorator:
    """Delete *build_dir* before building."""
    return mark.cocotb_clean(condition=condition)


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
    for marker in (
        cocotb_runner,
        cocotb_test,
        cocotb_timeout,
        cocotb_library,
        cocotb_sources,
        cocotb_defines,
        cocotb_includes,
        cocotb_parameters,
        cocotb_plusargs,
        cocotb_env,
        cocotb_seed,
        cocotb_timescale,
        cocotb_always,
        cocotb_clean,
        cocotb_waves,
        cocotb_build_args,
        cocotb_elab_args,
        cocotb_test_args,
        cocotb_pre_cmd,
    ):
        config.addinivalue_line("markers", _marker_description(marker))
