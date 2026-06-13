# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""A pytest plugin to integrate pytest with cocotb.

This plugin allows pytest to manage cocotb simulation runs and execute Python-based
HDL tests directly. It supports running simulations in subprocesses, compiling HDL
sources, and running cocotb coroutine tests in the simulator environment.

### Getting Started

To use this plugin, define a test function that accepts the ``dut`` fixture.
By default, the plugin compiles the HDL source code, launches the selected HDL simulator,
and runs your cocotb tests inside that simulator.

### Writing a Test

Here is a basic example of a pytest-cocotb test:

.. code-block:: python

    import pytest
    from pathlib import Path
    from cocotb.triggers import Timer


    # Configure the test using cocotb markers
    @pytest.mark.cocotb_sources(Path("rtl") / "my_design.sv")
    @pytest.mark.cocotb_toplevel("my_design")
    async def test_my_design(dut) -> None:
        # Drive inputs
        dut.rst.value = 1
        await Timer(10, units="ns")
        dut.rst.value = 0
        await Timer(10, units="ns")

        # Assert outputs
        assert dut.ready.value == 1

### Configuration Options

You can configure the plugin in three ways (ordered by precedence):

1. **Command-Line Arguments**: e.g., ``pytest --cocotb-simulator=verilator``
2. **Pytest Configuration File**: in ``pyproject.toml`` under ``[tool.pytest.ini_options]``:

   .. code-block:: toml

       [tool.pytest.ini_options]
       cocotb_simulator = "verilator"

3. **Environment Variables**: e.g., ``COCOTB_SIMULATOR=verilator``

For a complete list of configuration options, run ``pytest --help``.
"""

from __future__ import annotations

import os
import shlex
from argparse import ArgumentParser, Namespace
from pathlib import Path
from time import time

from pytest import (
    Config,
    FixtureRequest,
    OptionGroup,
    Parser,
    PytestPluginManager,
    fixture,
    hookimpl,
)

import cocotb
from cocotb.handle import SimHandleBase
from cocotb_tools.pytest import hookspecs
from cocotb_tools.pytest._option import Option, populate_ini_options
from cocotb_tools.pytest.dut import Dut
from cocotb_tools.pytest.mark import _register_markers
from cocotb_tools.runner import SUPPORTED_RUNNERS, Runner, get_runner

#: The default list of Python callables that start up the Python cosimulation environment.
_PYGPI_USERS: tuple[str, ...] = (
    "cocotb_tools._coverage:start_cocotb_library_coverage",
    "cocotb.logging:_configure",
    "cocotb._init:init_package_from_simulation",
)

#: List of pre-defined entry points with regression managers
_REGRESSION_MANAGER_ENTRY_POINT: dict[str, str] = {
    # TODO: Replace with pytest plugin
    "pytest": "cocotb.regression:_run_regression",
    "cocotb": "cocotb.regression:_run_regression",
}

#: List of cocotb options to set as environment variable.
_OPTION_ENVS: tuple[str, ...] = (
    "cocotb_trust_inertial_writes",
    "cocotb_waveform_viewer",
    "cocotb_scheduler_debug",
    "cocotb_log_level",
    "cocotb_resolve_x",
    "cocotb_attach",
    "gpi_log_level",
)

#: List of plugin options.
_OPTIONS: tuple[Option, ...] = (
    Option(
        "cocotb_regression_manager",
        choices=("pytest", "cocotb", "none"),
        default="pytest",
        description="""
            Select regression manager used to run cocotb tests. Available values:

            * ``pytest``: Use pytest to collect and run cocotb tests.
              This option allows to use pytest in fullness within HDL simulator and with cocotb tests.
              Cocotb runner is not needed. DUT is defined by using the pytest ``dut`` fixture and ``@pytest.mark.cocotb_*`` markers.
            * ``cocotb``: Use built-in cocotb regression manager.
              Cannot use pytest within HDL simulator or with cocotb tests.
              It requires to use cocotb runner in a separate test function defined in a separate test file to run cocotb tests.
            * ``none``: Don't use any pre-defined regression manager.
              This option, alongside with the :envvar:`PYGPI_USERS`` environment variable, will allow to use a custom regression manager.
        """,
    ),
    Option(
        "cocotb_summary",
        action="store_true",
        description="Show cocotb test summary info.",
    ),
    Option(
        "cocotb_sim_time_unit",
        choices=("step", "fs", "ps", "ns", "us", "ms", "sec"),
        default="ns",
        description="Simulation time unit that will be used during tests reporting.",
    ),
    Option(
        "cocotb_gui",
        action="store_true",
        description="Enable the GUI mode in the simulator (if supported).",
    ),
    Option(
        "cocotb_waves",
        action="store_true",
        description="Enable wave traces dump for simulator (if supported)",
    ),
    Option(
        "cocotb_waveform_viewer",
        metavar="NAME",
        default="surfer",
        description="""
            The name of the waveform viewer executable to use (like surfer) when GUI mode is enabled for simulators
            that do not have a built-in waveform viewer (like Verilator) The executable name will be called with the
            name of the waveform file as the argument.
        """,
    ),
    Option(
        "cocotb_random_seed",
        metavar="INTEGER",
        default=int(time()),
        default_in_help="current epoch time in seconds",
        type=int,
        description="Seed the Python random module to recreate a previous test stimulus.",
    ),
    Option(
        "cocotb_attach",
        metavar="SECONDS",
        type=int,
        description="""
            Pause time value in seconds before the simulator start. If set to non-zero value, cocotb will print the
            process ID (PID) to attach to and wait the specified time in seconds before actually letting the
            simulator run.
        """,
    ),
    Option(
        "cocotb_plusargs",
        nargs="*",
        metavar="PLUSARG",
        description="""
            Plusargs are options that are starting with a plus (``+``) sign.  They are passed to the simulator and are
            also available within cocotb as cocotb.plusargs. In the simulator, they can be read by the
            Verilog/SystemVerilog system functions ``$test$plusargs`` and ``$value$plusargs``.
        """,
    ),
    Option(
        "cocotb_resolve_x",
        choices=("error", "weak", "zeros", "ones", "random"),
        description="""
            Defines how to resolve bits with a value of ``X``, ``Z``, ``U``, ``W``, or ``-`` when being converted to integer. Valid settings are:

            * ``error``:  Resolves nothing.
            * ``weak``:   Resolves ``L`` to 0 and ``H`` to 1.
            * ``zeros``:  Like weak, but resolves all other non-0/1 values to ``0``.
            * ``ones``:   Like weak, but resolves all other non-0/1 values to ``1``.
            * ``random``: Like weak, but resolves all other non-0/1 values randomly to either 0 or 1.

            There is also a slight difference in behavior of bool(logic).
            When this is set, bool(logic) treats all non-0/1 values as equivalent to 0.
            When this is not set, bool(logic) will fail on non-0/1 values.
            Warning: Using this feature is not recommended.
        """,
    ),
    Option(
        "cocotb_scheduler_debug",
        action="store_true",
        description="""
            Enable additional log output of the coroutine scheduler. This will default the value of debug, which
            can later be modified.
        """,
    ),
    Option(
        "cocotb_simulator",
        choices=("auto", *SUPPORTED_RUNNERS),
        default="auto",
        metavar="NAME",
        description="""
            Select HDL simulator for cocotb. The ``auto`` option will automatically pick one of available HDL
            simulators where precedence order is based on available choices for this argument, from the highest priority
            (most left) to the lowest priority (most right).
        """,
    ),
    Option(
        "cocotb_trust_inertial_writes",
        action="store_true",
        description="""
            It enables a mode which allows cocotb to trust that VPI/VHPI/FLI inertial writes are applied properly
            according to the respective standards. This mode can lead to noticeable performance improvements, and
            also includes some behavioral difference that are considered by the cocotb maintainers to be “better”.
            Not all simulators handle inertial writes properly, so use with caution. This is achieved by not
            scheduling writes to occur at the beginning of the ``ReadWrite`` mode, but instead trusting that the
            simulator’s inertial write mechanism is correct. This allows cocotb to avoid a VPI callback into Python
            to apply writes.
        """,
    ),
    Option(
        "cocotb_pytest_args",
        type=shlex.split,
        action="extend",
        metavar="ARGS",
        description="""
            By default, instance of pytest that is running from HDL simulator as regression manager for cocotb tests,
            will be called with the same command line arguments as pytest invoked by user from command line that
            is starting cocotb runners (HDL simulators). This option allows user to override it and pass own
            arguments to pytest instance that is running from HDL simulator process. For example,
            it can be used to set different verbosity levels or capture modes between them.
            Example: ``pytest -v --capture=no --cocotb-pytest-args='-vv --capture=fd'``
        """,
    ),
    Option(
        "cocotb_pytest_dir",
        default_in_help="current working directory",
        metavar="PATH",
        type=Path,
        description="Override path from where pytest was invoked.",
    ),
    Option(
        "cocotb_build_dir",
        default="sim_build",
        metavar="PATH",
        type=Path,
        description="Directory to run the build step in.",
    ),
    Option(
        "cocotb_sources",
        nargs="*",
        metavar="FILE",
        description="Extra source files.",
    ),
    Option(
        "cocotb_defines",
        nargs="*",
        metavar="NAME[=VALUE]",
        description="Extra defines to set.",
    ),
    Option(
        "cocotb_includes",
        nargs="*",
        metavar="PATH",
        type=Path,
        description="Extra Verilog include directories.",
    ),
    Option(
        "cocotb_parameters",
        nargs="*",
        metavar="NAME[=VALUE]",
        description="Extra Verilog parameters or VHDL generics.",
    ),
    Option(
        "cocotb_library",
        default="top",
        metavar="NAME",
        description="The library name to compile into.",
    ),
    Option(
        "cocotb_always",
        action="store_true",
        description="Always run the build step.",
    ),
    Option(
        "cocotb_clean",
        action="store_true",
        description="Delete build directory before building.",
    ),
    Option(
        "cocotb_verbose",
        action="store_true",
        description="Enable verbose messages.",
    ),
    Option(
        "cocotb_timescale",
        metavar="UNIT[/PRECISION]",
        description="Timescale containing time unit and time precision for simulation.",
    ),
    Option(
        "cocotb_env",
        metavar="NAME[=VALUE]",
        nargs="*",
        description="Extra environment variables to set.",
    ),
    Option(
        "cocotb_toplevel_library",
        default="top",
        metavar="NAME",
        description="The library name for HDL toplevel module.",
    ),
    Option(
        "cocotb_toplevel_lang",
        choices=("auto", "verilog", "vhdl"),
        default="auto",
        description="""
            Language of the HDL toplevel module.
            Can be set to notify tests about preferred language in multi-language HDL design.
            This is also used by simulators that support more than one interface
            (:term:`VPI`, :term:`VHPI`, or :term:`FLI`) to select the appropriate interface to start cocotb.
            When set to ``auto``, value will be automatically evaluated based on selected HDL simulator or
            list of HDL source files provided during build stage in instance of :class:`cocotb_tools.pytest.dut.Dut`.
        """,
    ),
    Option(
        "cocotb_gpi_interfaces",
        nargs="*",
        metavar="NAME",
        description="List of GPI interfaces to use, with the first one being the entry point.",
    ),
    Option(
        "cocotb_build_args",
        type=shlex.split,
        action="extend",
        metavar="ARGS",
        description="Extra build arguments for the simulator.",
    ),
    Option(
        "cocotb_elab_args",
        type=shlex.split,
        action="extend",
        metavar="ARGS",
        description="Extra elaboration arguments for the simulator.",
    ),
    Option(
        "cocotb_sim_args",
        type=shlex.split,
        action="extend",
        metavar="ARGS",
        description="Extra simulation arguments for the simulator.",
    ),
    Option(
        "cocotb_pre_cmd",
        type=shlex.split,
        action="extend",
        metavar="ARGS",
        description="Extra commands to run before simulation begins.",
    ),
    Option(
        "cocotb_test_filter",
        metavar="REGEXP",
        description="A regular expression matching names of test function(s) to run.",
    ),
    Option(
        "cocotb_log_level",
        choices=("trace", "debug", "info", "warning", "error", "critical"),
        description="""
            The default log level of all "cocotb" Python loggers. The default is unset, which means that the log
            level is inherited from the root logger. This behaves similarly to :const:`logging.NOTSET`.
        """,
    ),
    Option(
        "gpi_log_level",
        choices=("trace", "debug", "info", "warning", "error", "critical"),
        description="""
            The default log level of all "gpi" (the low-level simulator interface) loggers, including both Python
            and the native GPI logger. The default is unset, which means that the log level is inherited from the
            root logger. This behaves similarly to :const:`logging.NOTSET`.
        """,
    ),
    Option(
        "pygpi_users",
        nargs="*",
        metavar="MODULE:FUNCTION",
        default=_PYGPI_USERS,
        description="""
            The Python module and callable that starts up the Python cosimulation environment. User overloads can be
            used to enter alternative Python frameworks or to hook existing cocotb functionality. It is formatted as
            ``path.to.entry.module:entry_point.function,other_module:other_func``. The string before the colon is the
            Python module to import and the string following the colon is the object to call as the entry function.
            The entry function must be a callable matching this form: ``entry_function(argv: List[str]) -> None``
        """,
    ),
)


@fixture
def dut(request: FixtureRequest) -> Dut | SimHandleBase:
    """A pytest fixture that provides either an instance of :class:`cocotb_tools.pytest.dut.Dut` or a simulation handle to the DUT.

    When running outside the simulation (in the parent pytest process), this fixture retrieves or creates a :class:`~cocotb_tools.pytest.dut.Dut`
    instance, which is used to define build and simulation options.

    When running inside the simulation (within the simulator process), this fixture returns the simulation handle to the DUT,
    allowing the test to drive and monitor the design's signals. This handle is equivalent to :data:`cocotb.top`.

    Example usage:

    .. code-block:: python

        import pytest
        from cocotb.triggers import Timer


        @pytest.mark.cocotb_sources("my_design.sv")
        async def test_dut_reset(dut) -> None:
            dut.rst.value = 1
            await Timer(5, units="ns")
            dut.rst.value = 0
            await Timer(5, units="ns")
            assert dut.rst.value == 0

    Args:
        request: The pytest fixture request.

    Returns:
        A simulation handle to the DUT (equivalent to :data:`cocotb.top`) when :data:`cocotb.is_simulation` is :data:`True`.
        An instance of :class:`cocotb_tools.pytest.dut.Dut` when :data:`cocotb.is_simulation` is :data:`False`.
    """
    return cocotb.top if cocotb.is_simulation else Dut.create(request)


def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    """Registers cocotb command-line options and configuration settings with pytest.

    Args:
        parser: The pytest parser used to parse command-line arguments and configuration settings.
        pluginmanager: The pytest plugin manager.
    """
    group: OptionGroup = parser.getgroup("cocotb", description="cocotb options")

    for option in _OPTIONS:
        option.add_to_group(group)


def pytest_addhooks(pluginmanager: PytestPluginManager) -> None:
    """Registers cocotb-specific pytest hooks at plugin registration time.

    Args:
        pluginmanager: The pytest plugin manager.
    """
    pluginmanager.add_hookspecs(hookspecs)


@hookimpl(tryfirst=True)
def pytest_configure(config: Config) -> None:
    """Configures the cocotb plugin by registering markers and exporting settings to environment variables.

    Args:
        config: The pytest configuration object.
    """
    option: Namespace = config.option

    _register_markers(config)
    populate_ini_options(config, _OPTIONS)

    # All cocotb environment variables are captured as options by pytest plugin
    for name in _OPTION_ENVS:
        value: object = getattr(option, name, None)
        environment: str = name.upper()

        if value:
            os.environ[environment] = "1" if value is True else str(value)
        elif environment in os.environ:
            del os.environ[environment]

    entry_point: str | None = _REGRESSION_MANAGER_ENTRY_POINT.get(
        option.cocotb_regression_manager
    )

    if entry_point and entry_point not in option.pygpi_users:
        option.pygpi_users.append(entry_point)

    os.environ["PYGPI_USERS"] = ",".join(option.pygpi_users)


@hookimpl(trylast=True)
def pytest_cocotb_dut_create(request: FixtureRequest) -> Dut | None:
    """Creates a new instance of :class:`cocotb_tools.pytest.dut.Dut`.

    This is the default built-in implementation of this hook. It is invoked as a
    fallback if no other hook implementations are registered or if they return :data:`None`.

    Args:
        request: The pytest fixture request.

    Returns:
        A new instance of :class:`cocotb_tools.pytest.dut.Dut`, or :data:`None`.
    """
    return Dut(request)


@hookimpl(trylast=True)
def pytest_cocotb_dut_run(dut: Dut) -> object:
    """Compiles, elaborates, and runs the HDL module with the simulator and cocotb tests using :class:`cocotb_tools.runner.Runner`.

    This is the default built-in implementation of this hook. It is invoked as a
    fallback if no other hook implementations are registered or if they return :data:`None`.

    Args:
        dut: An instance of :class:`~cocotb_tools.pytest.dut.Dut` containing the required configuration.

    Returns:
        A non-:data:`None` value to stop hook execution and indicate success.
    """
    # Cache value of the dut.work_dir because dut.id, that is part of work_dir, is re-calculated each time when invoked
    work_dir: Path = dut.work_dir

    runner: Runner = get_runner(str(dut.simulator))

    runner.build(
        hdl_library=dut.library or "top",
        sources=dut.sources,
        includes=dut.includes,
        defines=dut.defines,
        parameters=dut.parameters,
        build_args=dut.build_args,
        hdl_toplevel=dut.toplevel,
        always=dut.always,
        build_dir=work_dir,
        cwd=work_dir,
        clean=dut.clean,
        verbose=dut.verbose,
        timescale=dut.timescale,
        waves=dut.waves,
    )

    runner.test(
        test_module=dut.test_modules,
        hdl_toplevel=dut.toplevel or "",
        hdl_toplevel_library=dut.library or "top",
        hdl_toplevel_lang=dut.toplevel_lang,
        gpi_interfaces=dut.gpi_interfaces or None,
        seed=dut.random_seed,
        elab_args=dut.elab_args,
        test_args=dut.sim_args,
        extra_env={k: str(v) for k, v in dut.env.items()},
        waves=dut.waves,
        gui=dut.gui,
        parameters=dut.parameters or None,
        build_dir=work_dir,
        test_dir=work_dir,
        pre_cmd=dut.pre_cmd or None,
        verbose=dut.verbose,
        timescale=dut.timescale,
        test_filter=dut.test_filter or None,
        results_xml=str(work_dir / "results.xml"),
    )

    return True


def _options_for_documentation() -> ArgumentParser:
    """Exposes the plugin options as an ArgumentParser for Sphinx documentation.

    This function assists the sphinx-argparse extension in generating documentation
    for the plugin's configuration options.

    Returns:
        An ArgumentParser populated with the plugin's configuration options.
    """
    parser = ArgumentParser()

    for option in _OPTIONS:
        parser.add_argument(option.argument, help=option.help, **option.kwargs)

    return parser
