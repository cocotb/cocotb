# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Plugin markers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from inspect import Parameter, signature
from typing import Callable, overload

from pytest import Config, MarkDecorator, mark

from cocotb.simtime import TimeUnit
from cocotb_tools.runner import (
    VHDL,
    PathLike,
    VerilatorControlFile,
    Verilog,
)


@overload
def cocotb_runner() -> MarkDecorator: ...


@overload
def cocotb_runner(*test_module: str) -> MarkDecorator: ...


@overload
def cocotb_runner(
    *test_module: str,
    library: str = "top",
    sources: Sequence[PathLike | VHDL | Verilog | VerilatorControlFile] = [],
    includes: Sequence[PathLike] = [],
    defines: Mapping[str, object] = {},
    parameters: Mapping[str, object] = {},
    build_args: Sequence[str | VHDL | Verilog] = [],
    toplevel_lang: str | None = None,
    always: bool = False,
    clean: bool = False,
    verbose: bool = False,
    timescale: tuple[str, str] | None = None,
    waves: bool = False,
    toplevel_library: str = "top",
    gpi_interfaces: list[str] | None = None,
    seed: str | int | None = None,
    elab_args: Sequence[str] = [],
    test_args: Sequence[str] = [],
    plusargs: Sequence[str] = [],
    env: Mapping[str, str] = {},
    gui: bool = False,
    pre_cmd: list[str] | None = [],
) -> MarkDecorator: ...


def cocotb_runner(*test_module: str, **option: object) -> MarkDecorator:
    """Mark test function as cocotb runner.

    Example usage:

    .. code:: python

        import pytest
        from cocotb_tools.pytest.hdl import HDL

        @pytest.fixture(name="sample_module")
        def sample_module_fixture(hdl: HDL) -> HDL:
            # Define HDL design and build it
            hdl.toplevel = "sample_module"
            hdl.sources = (DESIGNS / "sample_module.sv",)
            hdl.build()

            return hdl

        @pytest.mark.cocotb_runner
        def test_dut(sample_module: HDL) -> None:
            # Run HDL simulator with cocotb tests
            sample_module.test()

    Args:
        test_module:
            Name of Python module with cocotb tests to be loaded by cocotb :py:attr:`~cocotb_tools.pytest.hdl.HDL.runner`.

        library:
            The library name to compile into.

        sources:
            Language-agnostic list of source files to build.

        includes:
            Verilog include directories.

        defines:
            Defines to set.

        parameters:
            Verilog parameters or VHDL generics.

        build_args:
            Extra build arguments for the simulator.

        always:
            Always run the build step.

        clean:
            Delete *build_dir* before building.

        verbose:
            Enable verbose messages.

        timescale:
            Tuple containing time unit and time precision for simulation.

        waves:
            Record signal traces.

        toplevel_library:
            The library name for HDL toplevel module.

        gpi_interfaces:
            List of GPI interfaces to use, with the first one being the entry point.

        seed:
            A specific random seed to use.

        elab_args:
            A list of elaboration arguments for the simulator.

        test_args:
            A list of extra arguments for the simulator.

        plusargs:
            'plusargs' to set for the simulator.

        env:
            Extra environment variables to set.

        gui:
            Run with simulator GUI.

        pre_cmd:
            Commands to run before simulation begins. Typically Tcl commands for simulators that support them.

    Returns:
        Decorated test function as cocotb runner.
    """
    return mark.cocotb_runner(*test_module, **option)


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

        @pytest.mark.cocotb_timeout(200, "ns")
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


def marker_description(marker: Callable[..., MarkDecorator]) -> str:
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
            args.extend(("...", "*"))

    description: str = str(marker.__doc__).lstrip().splitlines()[0]

    return f"{marker.__name__}({', '.join(args)}): {description}".rstrip()


def register_markers(config: Config) -> None:
    """Register plugin markers.

    Args:
        config: Pytest configuration object.
    """
    config.addinivalue_line("markers", marker_description(cocotb_runner))
    config.addinivalue_line("markers", marker_description(cocotb_test))
    config.addinivalue_line("markers", marker_description(cocotb_timeout))
