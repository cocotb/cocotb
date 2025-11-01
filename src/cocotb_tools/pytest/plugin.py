# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Pytest plugin to integrate pytest with cocotb."""

from __future__ import annotations

import inspect
import os
import shlex
import textwrap
from argparse import ArgumentParser
from collections.abc import Iterable
from pathlib import Path
from time import time
from typing import Any

from pytest import (
    Class,
    Collector,
    Config,
    ExitCode,
    FixtureRequest,
    Function,
    Item,
    Mark,
    Module,
    Parser,
    PytestPluginManager,
    TerminalReporter,
    TestReport,
    fixture,
    hookimpl,
    mark,
)

import cocotb
import cocotb.handle
from cocotb.handle import SimHandleBase
from cocotb_tools.pytest.compat import (
    cocotb_decorator_as_pytest_marks,
    is_cocotb_decorator,
)
from cocotb_tools.pytest.controller import Controller
from cocotb_tools.pytest.hdl import HDL, SIMULATORS
from cocotb_tools.pytest.mark import register_markers
from cocotb_tools.pytest.option import Option, add_options_to_parser, is_cocotb_option


def to_timescale(value: str) -> tuple[str, str]:
    """Split string containing timescale to time unit and time precision.

    Args:
        value: Timescale in format of ``UNIT[/PRECISION]``.

    Returns:
        Time unit and time precision based on provided timescale.
    """
    time_unit, _, time_precision = value.partition("/")

    time_unit = time_unit.strip()
    time_precision = time_precision.strip()

    return time_unit, time_precision or time_unit


def to_dict(items: Iterable[str]) -> dict[str, object]:
    """Convert list of items into dictionary.

    Args:
        items: List of items in form of ``NAME=VALUE``.

    Returns:
        List of items as dictionary.
    """
    result: dict[str, object] = {}

    for item in items:
        name, _, value = item.partition("=")
        result[name] = value

    return result


ENTRY_POINTS: dict[str, str] = {
    "pytest": "cocotb_tools.pytest._init:run_regression",
    "cocotb": "cocotb._init:run_regression",
}


OPTIONS: tuple[Option, ...] = (
    Option(
        "cocotb_regression_manager",
        choices=("pytest", "cocotb", "none"),
        default="pytest",
        description="""
            Regression manager that will be used to run cocotb tests:

            * ``pytest``: Use pytest as regression manager to manage and run cocotb tests.
            * ``cocotb``: Use built-in cocotb regression manager to manage and run cocotb tests.
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
        description="Enable wave traces dump for simulator (if supported).",
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
        "cocotb_seed",
        metavar="INTEGER",
        default=int(time()),
        default_in_help="current epoch time in seconds",
        environment="COCOTB_RANDOM_SEED",
        type=int,
        description="Seed the Python random module to recreate a previous test stimulus.",
    ),
    Option(
        "cocotb_ansi_output",
        choices=("yes", "no", "auto"),
        default="auto",
        description="""
            Override the default behavior of annotating cocotb output with ANSI color codes if the output is a terminal:

            * ``yes``: Forces output to be ANSI-colored regardless of the type of stdout or the presence of :envvar:`NO_COLOR`.
            * ``no``:  Suppresses the ANSI color output in the log messages.
        """,
    ),
    Option(
        "cocotb_attach",
        metavar="SECONDS",
        default=0,
        type=int,
        description="""
            Pause time value in seconds before the simulator start. If set to non-zero value, cocotb will print the
            process ID (PID) to attach to and wait the specified time in seconds before actually letting the
            simulator run.
        """,
    ),
    Option(
        "cocotb_enable_profiling",
        action="store_true",
        description="""
            Enable performance analysis of the Python portion of cocotb. When enabled, a file test_profile.pstat
            will be written which contains statistics about the cumulative time spent in the functions. From this,
            a callgraph diagram can be generated with gprof2dot and graphviz.
        """,
    ),
    Option(
        "cocotb_log_level",
        choices=("trace", "debug", "info", "warning", "error", "critical"),
        description="""
            The default log level of all "cocotb" Python loggers. The default is unset, which means that the log
            level is inherited from the root logger. This behaves similarly to :py:const:`logging.INFO`.
        """,
    ),
    Option(
        "cocotb_log_prefix",
        metavar="FORMAT",
        description="""
            Customize the log message prefix. The value of this variable should be in Python f-string syntax.
            It has access to the following variables:

            * ``record``:  The :py:class:`logging.LogRecord` being formatted. This includes the attribute ``created_sim_time``, which is the simulation time in steps.
            * ``time``:    The Python :py:mod:`time` module.
            * ``simtime``: The cocotb :py:mod:`cocotb.simtime` module.
            * ``ANSI``:    The cocotb :py:const:`cocotb.logging.ANSI` enum, which contains ANSI escape codes for coloring the output.
        """,
    ),
    Option(
        "cocotb_plusargs",
        nargs="*",
        default=[],
        metavar="PLUSARG",
        description="""
            Plusargs are options that are starting with a plus (``+``) sign.  They are passed to the simulator and are
            also available within cocotb as cocotb.plusargs. In the simulator, they can be read by the
            Verilog/SystemVerilog system functions ``$test$plusargs`` and ``$value$plusargs``.
        """,
    ),
    Option(
        "cocotb_reduced_log_fmt",
        choices=("yes", "no"),
        default="yes",
        description="""
            * ``yes``: Logs will include simulation time, message type (INFO, WARNING, ERROR, ...), logger name, and the log message itself.
            * ``no``:  The filename and line number where a log function was called will be added between the logger name and the log message.
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
        choices=("auto", *tuple(SIMULATORS.values())),
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
        "cocotb_user_coverage",
        action="store_true",
        description="""
            Enable to collect Python coverage data for user code. For some simulators, this will also report HDL
            coverage. If coverage configuration file doesn't exist, branch coverage is collected and files in the
            cocotb package directory are excluded. This needs the coverage Python module to be installed.
        """,
    ),
    Option(
        "cocotb_pytest_args",
        type=shlex.split,
        default=[],
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
        "cocotb_defines",
        nargs="*",
        metavar="NAME[=VALUE]",
        default=[],
        description="Extra defines to set.",
    ),
    Option(
        "cocotb_includes",
        nargs="*",
        metavar="PATH",
        default=[],
        type=Path,
        description="Extra Verilog include directories.",
    ),
    Option(
        "cocotb_parameters",
        nargs="*",
        metavar="NAME[=VALUE]",
        default=[],
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
        default="1ns/1ns",
        metavar="UNIT[/PRECISION]",
        description="Timescale containing time unit and time precision for simulation.",
    ),
    Option(
        "cocotb_env",
        metavar="NAME[=VALUE]",
        nargs="*",
        default=[],
        description="Extra environment variables to set.",
    ),
    Option(
        "cocotb_toplevel_library",
        default="top",
        metavar="NAME",
        description="The library name for HDL toplevel module.",
    ),
    Option(
        "cocotb_gpi_interfaces",
        nargs="*",
        metavar="NAME",
        default=[],
        description="List of GPI interfaces to use, with the first one being the entry point.",
    ),
    Option(
        "cocotb_build_args",
        type=shlex.split,
        default=[],
        metavar="ARGS",
        description="Extra build arguments for the simulator.",
    ),
    Option(
        "cocotb_elab_args",
        type=shlex.split,
        default=[],
        metavar="ARGS",
        description="Extra elaboration arguments for the simulator.",
    ),
    Option(
        "cocotb_test_args",
        type=shlex.split,
        default=[],
        metavar="ARGS",
        description="Extra arguments for the simulator.",
    ),
    Option(
        "cocotb_pre_cmd",
        type=shlex.split,
        default=[],
        metavar="ARGS",
        description="Extra commands to run before simulation begins.",
    ),
    Option(
        "gpi_log_level",
        choices=("trace", "debug", "info", "warning", "error", "critical"),
        description="""
            The default log level of all "gpi" (the low-level simulator interface) loggers, including both Python
            and the native GPI logger. The default is unset, which means that the log level is inherited from the
            root logger. This behaves similarly to :py:const:`logging.INFO`.
        """,
    ),
    Option(
        "pygpi_users",
        nargs="*",
        metavar="MODULE:FUNCTION",
        default=(
            "cocotb_tools._coverage:start_cocotb_library_coverage",
            "cocotb.logging:_configure",
            "cocotb._init:init_package_from_simulation",
        ),
        description="""
            The Python module and callable that starts up the Python cosimulation environment. User overloads can be
            used to enter alternative Python frameworks or to hook existing cocotb functionality. It is formatted as
            ``path.to.entry.module:entry_point.function,other_module:other_func``. The string before the colon is the
            Python module to import and the string following the colon is the object to call as the entry function.
            The entry function must be a callable matching this form: ``entry_function(argv: List[str]) -> None``
        """,
    ),
)


def options_for_documentation() -> ArgumentParser:
    """It helps to attach plugin options into Sphinx documentation using the sphinx-argparse extension."""
    parser: ArgumentParser = ArgumentParser(
        prog="pytest",
        description="Plugin options",
    )

    for option in OPTIONS:
        default: Any

        if option.extra.get("action") == "store_true":
            default = False
        else:
            default = option.default_in_help or option.default

        parser.add_argument(
            option.argument,
            help=(
                f"{textwrap.dedent(option.description)}\n\n"
                f"Configuration option: ``{option.name}``\n\n"
                f"Environment variable: :envvar:`{option.environment}`"
            ),
            default=default,
            **option.extra,
        )

    return parser


@fixture(name="dut", scope="session")
def dut_fixture() -> SimHandleBase | None:
    """Simulation handle to DUT."""
    return getattr(cocotb, "top", None)


@fixture(name="hdl")
def hdl_fixture(request: FixtureRequest) -> HDL:
    """HDL design."""
    return HDL(request)


def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    add_options_to_parser(parser, "cocotb", OPTIONS)


@hookimpl(tryfirst=True)
def pytest_configure(config: Config) -> None:
    option = config.option

    register_markers(config)

    if option.pygpi_users is None:
        option.pygpi_users = config.getini("pygpi_users")

    if option.cocotb_regression_manager is None:
        option.cocotb_regression_manager = config.getini("cocotb_regression_manager")

    entry_point: str | None = ENTRY_POINTS.get(option.cocotb_regression_manager)

    if entry_point and entry_point not in option.pygpi_users:
        option.pygpi_users.append(entry_point)

    # Iterate over all command line arguments, load default value from configuration files,
    # set or unset environment variables
    for name, optval in vars(option).items():
        if is_cocotb_option(name):
            value: Any = optval

            if value is None:
                value = config.getini(name)
                setattr(option, name, value)

            environment: str = name.upper()

            # Set value of environment variable to be understable by cocotb
            if value in (True, "yes"):
                os.environ[environment] = "1"
            elif value in (False, "no", "none", "auto", "", []):
                if environment in os.environ:
                    del os.environ[environment]
            elif isinstance(value, list):
                os.environ[environment] = ",".join(value)
            else:
                os.environ[environment] = str(value)

    if isinstance(option.cocotb_timescale, str):
        option.cocotb_timescale = to_timescale(option.cocotb_timescale)

    if isinstance(option.cocotb_env, list):
        option.cocotb_env = to_dict(option.cocotb_env)

    if isinstance(option.cocotb_defines, list):
        option.cocotb_defines = to_dict(option.cocotb_defines)

    if isinstance(option.cocotb_parameters, list):
        option.cocotb_parameters = to_dict(option.cocotb_parameters)

    os.environ["COCOTB_PYTEST_DIR"] = (
        str(Path(option.cocotb_pytest_dir).resolve())
        if option.cocotb_pytest_dir
        else str(config.invocation_params.dir)
    )

    os.environ["COCOTB_PYTEST_ARGS"] = shlex.join(
        option.cocotb_pytest_args or config.invocation_params.args
    )

    if option.color == "yes":
        os.environ["COCOTB_ANSI_OUTPUT"] = "1"
    elif option.color == "no" or option.cocotb_ansi_output == "no":
        os.environ["COCOTB_ANSI_OUTPUT"] = "0"

    if option.cocotb_reduced_log_fmt == "no":
        os.environ["COCOTB_REDUCED_LOG_FMT"] = "0"

    if option.cocotb_gui:
        os.environ["GUI"] = "1"

    if option.cocotb_waves:
        os.environ["WAVES"] = "1"

    coverage_rcfile: str | None = getattr(option, "cov_config", None)

    if coverage_rcfile and Path(coverage_rcfile).exists():
        os.environ["COVERAGE_RCFILE"] = coverage_rcfile

    if not config.pluginmanager.hasplugin("cocotb_regression_manager"):
        config.pluginmanager.register(Controller(config), "cocotb_controller")


@hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(
    collector: Module | Class, name: str, obj: object
) -> Item | Collector | list[Item | Collector] | None:
    if is_cocotb_decorator(obj):
        obj = cocotb_decorator_as_pytest_marks(collector, name, obj)

        return collector.config.hook.pytest_pycollect_makeitem(
            collector=collector, name=name, obj=obj
        )

    if inspect.isfunction(obj):
        markers: list[Mark] | None = getattr(obj, "pytestmark", None)

        if any(marker.name == "cocotb" for marker in markers or ()):
            setattr(obj, "__test__", True)

        elif (
            inspect.iscoroutinefunction(obj)
            and "dut" in inspect.signature(obj).parameters
        ):
            marker: Mark = mark.cocotb().mark

            if markers is None:
                setattr(obj, "pytestmark", [marker])
            else:
                markers.append(marker)

    return None


def is_cocotb_test(item: Item) -> bool:
    """Check if provided pytest item is cocotb test.

    Args:
        item: Pytest item (test).

    Returns:
        True if provided pytest item is cocotb test. Otherwise False.
    """
    return (
        isinstance(item, Function)
        and "cocotb" in item.keywords
        and inspect.iscoroutinefunction(item.function)
    )


def is_cocotb_test_report(item: Any) -> bool:
    """Check if provided pytest item is cocotb test report.

    Args:
        item: Pytest item (test report).

    Returns:
        True if provided pytest item is cocotb test report. Otherwise False.
    """
    return isinstance(item, TestReport) and getattr(item, "cocotb", False)


@hookimpl(tryfirst=True)
def pytest_terminal_summary(
    terminalreporter: TerminalReporter,
    exitstatus: ExitCode,
    config: Config,
) -> None:
    if not config.option.cocotb_summary:
        return

    terminalreporter.section("cocotb test summary info", cyan=True, bold=True)
    sim_time_unit: str = config.option.cocotb_sim_time_unit

    summary: tuple[list[str], ...] = (
        ["TEST"],
        ["STATUS"],
        [f"SIM TIME ({sim_time_unit})"],
        ["REAL TIME (s)"],
        [f"RATIO ({sim_time_unit}/s)"],
    )

    map_status: dict[str, str] = {
        "passed": "PASS",
        "failed": "FAIL",
        "skipped": "SKIP",
        "xfailed": "PASS",
        "xpassed": "FAIL",
    }

    count: dict[str, int] = {
        "PASS": 0,
        "FAIL": 0,
        "SKIP": 0,
    }

    status_markups: dict[str, tuple[str, ...]] = {
        "PASS": ("green",),
        "FAIL": ("red",),
        "SKIP": ("yellow",),
    }

    widths: list[int] = [len(column[0]) for column in summary]
    aligns: tuple[str, ...] = ("<", "^", ">", ">", ">")
    sum_sim_time: float = 0
    sum_real_time: float = 0
    tests: int = 0

    for status, items in terminalreporter.stats.items():
        if status in ("passed", "failed", "skipped", "xfailed", "xpassed"):
            test_status = map_status[status]

            for item in items:
                if is_cocotb_test_report(item):
                    count[test_status] += 1
                    tests += 1

                    sim_time: float = getattr(item, "sim_time_duration", 0)
                    real_time: float = getattr(item, "duration", 0)
                    ratio: float = sim_time / real_time if real_time else 0

                    sum_sim_time += sim_time
                    sum_real_time += real_time

                    summary[0].append(item.nodeid)
                    summary[1].append(test_status)
                    summary[2].append(f"{sim_time:.2f} ")
                    summary[3].append(f"{real_time:.2f} ")
                    summary[4].append(f"{ratio:.2f} ")

                    for index, column_width in enumerate(widths):
                        widths[index] = max(column_width, len(summary[index][-1]))

    sum_ratio = sum_sim_time / sum_real_time if sum_real_time else 0
    passed: int = count["PASS"]
    failed: int = count["FAIL"]
    skipped: int = count["SKIP"]

    summary[0].append(f"TESTS={tests} PASS={passed} FAIL={failed} SKIP={skipped}")
    summary[1].append("")
    summary[2].append(f"{sum_sim_time:.2f} ")
    summary[3].append(f"{sum_real_time:.2f} ")
    summary[4].append(f"{sum_ratio:.2f} ")

    rows: int = len(summary[0])
    columns: int = len(summary)
    last: int = rows - 1

    for row in range(rows):
        if row == last:
            terminalreporter.write_sep("-")

        terminalreporter.write("**")

        for column in range(columns):
            value: Any = summary[column][row]
            width: int = widths[column]
            align: str = aligns[column]
            markups: dict[str, bool] = {}

            if column == 1 and row not in (0, last):
                markups = dict.fromkeys(status_markups[value], True)

            terminalreporter.write(f" {{:{align}{width}}} ".format(value), **markups)

        terminalreporter.write("**\n")
        terminalreporter.ensure_newline()

        if row == 0:
            terminalreporter.write_sep("-")

    terminalreporter.flush()
