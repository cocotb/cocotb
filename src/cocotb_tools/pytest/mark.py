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


def cocotb() -> MarkDecorator:
    """Marks the pytest node or item as a cocotb node/item (build, test module, simulation, test).

    This marker is automatically set by the cocotb pytest plugin on all discovered cocotb tests.

    To collect/run only cocotb tests:

    .. code-block:: shell

        pytest -m cocotb

    To collect/run non-cocotb tests:

    .. code-block:: shell

        pytest -m 'not cocotb'
    """
    return mark.cocotb()


def cocotb_simulation() -> MarkDecorator:
    """Marks the pytest item as an HDL simulation that runs cocotb tests.

    This marker is automatically set by the cocotb pytest plugin on all created pytest items that run HDL simulations with cocotb tests.
    """
    return mark.cocotb_simulation()


def cocotb_test() -> MarkDecorator:
    """Marks the test function as a cocotb test.

    This marker is automatically set by the cocotb pytest plugin on all discovered cocotb tests.
    """
    return mark.cocotb_test()


def cocotb_suffix(name: str, /) -> MarkDecorator:
    """Add the suffix to name of :class:`cocotb_tools.pytest.dut.Dut` fixture.

    It helps to identify DUTs that are using the same name of the HDL library and top level design but
    different compilation, elaboration or simulation arguments.

    Example usage:

    .. code-block:: python

        # test_*.py
        import pytest


        @pytest.mark.cocotb_toplevel("top")
        @pytest.mark.cocotb_timescale("1ns")
        @pytest.mark.cocotb_suffix("with_timescale_1ns")
        async def test_dut_feature_1(dut) -> None: ...


        @pytest.mark.cocotb_toplevel("top")
        @pytest.mark.cocotb_timescale("1ps")
        @pytest.mark.cocotb_suffix("with_timescale_1ps")
        async def test_dut_feature_2(dut) -> None: ...

    Args:
        name: Suffix added to name of :class:`cocotb_tools.pytest.dut.Dut` fixture.
    """
    return mark.cocotb_suffix(name)


def cocotb_simulator(name: str, /) -> MarkDecorator:
    """Selects the HDL simulator to use.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_simulator("verilator"),)

    Args:
        name: Name of HDL simulator.
    """
    return mark.cocotb_simulator(name)


def cocotb_test_modules(*modules: str) -> MarkDecorator:
    """Adds Python modules containing cocotb tests to run.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (
            pytest.mark.cocotb_test_modules(
                "tests.test_module_1",
                "tests.test_module_2",
            ),
        )

    Args:
        *modules: Name of Python module(s) that will be imported.
    """
    return mark.cocotb_test_modules(*modules)


def cocotb_toplevel(name: str, /) -> MarkDecorator:
    """Sets the name of the HDL toplevel module.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_toplevel("top"),)

    Args:
        name: Name of HDL toplevel module.
    """
    return mark.cocotb_toplevel(name)


def cocotb_toplevel_lang(name: str, /) -> MarkDecorator:
    """Sets the language of the HDL toplevel module.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_toplevel_lang("verilog"),)

    Args:
        name: Language of the HDL toplevel module. Supported values: ``verilog`` or ``vhdl``.
    """
    return mark.cocotb_toplevel_lang(name)


def cocotb_toplevel_library(name: str, /) -> MarkDecorator:
    """Sets the library name for the HDL toplevel module.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_toplevel_library("toplib"),)

    Args:
        name: Library name for the HDL toplevel module.
    """
    return mark.cocotb_toplevel_library(name)


def cocotb_timeout(duration: float, unit: TimeUnit) -> MarkDecorator:
    """Marks a coroutine test function with a simulation time limit after which the test is forced to fail.

    Example usage:

    .. code-block:: python

        @pytest.mark.cocotb_timeout(duration=200, unit="ns")
        async def test_dut_feature_with_timeout(dut) -> None:
            # Test DUT feature with timeout configured from cocotb marker
            ...

    Args:
        duration: The simulation time duration before the test is forced to fail.
        unit: The simulation time unit (accepts any unit supported by :class:`~cocotb.triggers.Timer`).

    Raises:
        :exc:`~cocotb.triggers.SimTimeoutError`: The test function timed out.

    Returns:
        The decorated coroutine function.
    """
    return mark.cocotb_timeout(duration=duration, unit=unit)


def cocotb_sources(
    *sources: PathLike | Verilog | VHDL | VerilatorControlFile,
) -> MarkDecorator:
    """Adds a list of language-agnostic source files to build.

    Example usage:

    .. code-block:: python

        from pathlib import Path
        import pytest

        DIR: Path = Path(__file__).parent.resolve()

        pytestmark = (
            pytest.mark.cocotb_sources(
                DIR / "rtl" / "adder.sv",
                DIR / "rtl" / "alu.sv",
            ),
        )

    Args:
        *sources: The source files to be compiled.
    """
    return mark.cocotb_sources(*sources)


def cocotb_defines(**defines: object) -> MarkDecorator:
    """Sets Verilog/SystemVerilog preprocessor defines when compiling HDL source files.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (
            pytest.mark.cocotb_defines(
                DEFINE1="string",
                DEFINE2=1234,
                DEFINE3=3.14,
                DEFINE4=True,
            ),
        )

    Args:
        **defines: The preprocessor defines to set.
    """
    return mark.cocotb_defines(**defines)


def cocotb_parameters(**parameters: object) -> MarkDecorator:
    """Sets Verilog/SystemVerilog parameters and VHDL generics when elaborating the HDL toplevel module.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (
            pytest.mark.cocotb_parameters(
                PARAM1="string",
                PARAM2=1234,
                PARAM3=3.14,
            ),
        )


        # test_*.py
        async def test_dut_feature_1(dut) -> None:
            assert dut.PARAM1 == "string"
            assert dut.PARAM2 == 1234
            assert dut.PARAM3 == 3.14

    Args:
        **parameters: The parameters and generics to set.
    """
    return mark.cocotb_parameters(**parameters)


def cocotb_env(**env: object) -> MarkDecorator:
    """Sets environment variables that will be available to the running HDL simulation and cocotb tests.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import os
        import pytest

        pytestmark = (
            pytest.mark.cocotb_env(
                ENV1="string",
                ENV2=1234,
                ENV3=3.14,
                ENV4=True,
            ),
        )


        # test_*.py
        async def test_dut_feature_1(dut) -> None:
            assert os.getenv("ENV1") == "string"
            assert int(os.getenv("ENV2", 0)) == 1234
            assert float(os.getenv("ENV3", 0)) == 3.14
            assert bool(os.getenv("ENV4", False)) == True

    Args:
        **env: The environment variables to set.
    """
    return mark.cocotb_env(**env)


def cocotb_includes(*includes: PathLike) -> MarkDecorator:
    """Adds include directories for Verilog or SystemVerilog compilation.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        from pathlib import Path
        import pytest

        DIR: Path = Path(__file__).parent.resolve()

        pytestmark = (
            pytest.mark.cocotb_includes(
                DIR / "rtl" / "adder",
                DIR / "rtl" / "alu",
            ),
        )

    Args:
        *includes: Include directories to add.
    """
    return mark.cocotb_includes(*includes)


def cocotb_plusargs(*plusargs: str) -> MarkDecorator:
    """Adds plus arguments (``+arg``) for the simulator.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (
            pytest.mark.cocotb_plusargs(
                "+arg1",
                "+arg2=value",
            ),
        )

    Args:
        *plusargs: Plus arguments to pass to the simulator.
    """
    return mark.cocotb_plusargs(*plusargs)


def cocotb_timescale(value: str | tuple[str, str] | None, /) -> MarkDecorator:
    """Sets the time unit and time precision for the simulation.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_timescale("1ns / 1ps"),)

    Args:
        value: A string (e.g. ``"1ns/1ps"``) or a tuple (e.g. ``("1ns", "1ps")``) specifying the timescale.
    """
    return mark.cocotb_timescale(value)


def cocotb_build_dir(path: PathLike, /) -> MarkDecorator:
    """Sets the directory in which the build step is run.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_build_dir("build"),)

    Args:
        path: The path or name of the build directory.
    """
    return mark.cocotb_build_dir(path)


def cocotb_build_args(*args: str | VHDL | Verilog) -> MarkDecorator:
    """Adds extra compilation/build arguments for the simulator.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (
            pytest.mark.cocotb_build_args(
                "-arg1",
                "-arg2",
                "value",
            ),
        )

    Args:
        *args: Extra build arguments to pass to the simulator during compilation.
    """
    return mark.cocotb_build_args(*args)


def cocotb_elab_args(*args: str) -> MarkDecorator:
    """Adds extra elaboration arguments for the simulator.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (
            pytest.mark.cocotb_elab_args(
                "-arg1",
                "-arg2",
                "value",
            ),
        )

    Args:
        *args: Extra elaboration arguments to pass to the simulator.
    """
    return mark.cocotb_elab_args(*args)


def cocotb_sim_args(*args: str) -> MarkDecorator:
    """Adds extra simulation (runtime) arguments for the simulator.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_sim_args("-v", "+some_sim_option"),)

    Args:
        *args: Extra simulation arguments.
    """
    return mark.cocotb_sim_args(*args)


def cocotb_pre_cmd(*args: str) -> MarkDecorator:
    """Adds extra commands to run before the simulation begins.

    These are typically Tcl commands for simulators that support them (e.g., ModelSim/Questa).

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_pre_cmd("run 0", "log -r /*"),)

    Args:
        *args: Commands to run before the simulation starts.
    """
    return mark.cocotb_pre_cmd(*args)


def cocotb_library(name: str, /) -> MarkDecorator:
    """Sets the library name to compile HDL sources into.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_library("my_lib"),)

    Args:
        name: The name of the library.
    """
    return mark.cocotb_library(name)


def cocotb_waves(enable: bool = True, /) -> MarkDecorator:
    """Enables or disables recording of signal traces (waveforms).

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_waves,)

    Args:
        enable: Whether to enable waveform recording.
    """
    return mark.cocotb_waves(enable)


def cocotb_verbose(enable: bool = True, /) -> MarkDecorator:
    """Enables or disables verbose output from the simulator runner.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_verbose,)

    Args:
        enable: Whether to enable verbose messages.
    """
    return mark.cocotb_verbose(enable)


def cocotb_always(enable: bool = True, /) -> MarkDecorator:
    """Forces the compilation/build step to run, even if sources have not changed.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_always,)

    Args:
        enable: Whether to always run the build step.
    """
    return mark.cocotb_always(enable)


def cocotb_clean(enable: bool = True, /) -> MarkDecorator:
    """Deletes the build directory before starting a new build.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_clean,)

    Args:
        enable: Whether to delete the build directory before building.
    """
    return mark.cocotb_clean(enable)


def cocotb_gui(enable: bool = True, /) -> MarkDecorator:
    """Enables the GUI mode in the simulator, if supported.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_gui,)

    Args:
        enable: Whether to enable GUI mode.
    """
    return mark.cocotb_gui(enable)


def cocotb_gpi_interfaces(*args: str) -> MarkDecorator:
    """Specifies the list of GPI interfaces to use, with the first one being the entry point.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_gpi_interfaces("vpi", "vhpi"),)

    Args:
        *args: GPI interfaces to load.
    """
    return mark.cocotb_gpi_interfaces(*args)


def cocotb_test_filter(regexp: str, /) -> MarkDecorator:
    """Specifies a regular expression to filter and match names of cocotb test functions to run.

    Example usage:

    .. code-block:: python

        # conftest.py or test_*.py
        import pytest

        pytestmark = (pytest.mark.cocotb_test_filter("test_alu_.*"),)

    Args:
        regexp: A regular expression matching names of test functions to run.
    """
    return mark.cocotb_test_filter(regexp)


def _marker_description(marker: Callable) -> str:
    """Return a formatted description of the marker.

    Args:
        marker: The marker callable.

    Returns:
        A formatted description string for the marker.
    """
    args: list[str] = []
    positional_only: bool = False

    for name, parameter in signature(marker).parameters.items():
        arg: str = ""

        if parameter.kind == Parameter.VAR_POSITIONAL:
            arg += "*"
        elif parameter.kind == Parameter.VAR_KEYWORD:
            arg += "**"

        if parameter.kind == Parameter.POSITIONAL_ONLY:
            positional_only = True

        arg += name

        if parameter.default != Parameter.empty:
            arg += f"={parameter.default}"

        args.append(arg)

    if positional_only:
        args.append("/")

    description: str = str(marker.__doc__).lstrip().splitlines()[0]

    return f"{marker.__name__}({', '.join(args)}): {description}".rstrip()


def _register_markers(config: Config) -> None:
    """Register all cocotb-specific markers with the pytest configuration.

    Args:
        config: The pytest configuration object.
    """
    for name, value in globals().items():
        if name.startswith("cocotb") and callable(value):
            config.addinivalue_line("markers", _marker_description(value))
