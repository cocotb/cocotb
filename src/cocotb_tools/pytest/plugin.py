# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Pytest plugin to integrate pytest with cocotb."""

from __future__ import annotations

import inspect
import shlex
import textwrap
from argparse import ArgumentParser
from collections.abc import Generator, Iterable, Mapping
from pathlib import Path
from time import time
from typing import Any, TYPE_CHECKING

from pluggy import Result
from pytest import (
    Class,
    Collector,
    CollectReport,
    Config,
    ExitCode,
    FixtureRequest,
    Item,
    Mark,
    Module,
    Parser,
    PytestPluginManager,
    TerminalReporter,
    TestReport,
    TestShortLogReport,
    fixture,
    hookimpl,
    mark,
)

import cocotb
import cocotb.handle
from cocotb.handle import SimHandleBase
from cocotb_tools.pytest import hookspecs
from cocotb_tools.pytest._compat import (
    cocotb_decorator_as_pytest_marks,
    is_cocotb_decorator,
)
from cocotb_tools.pytest._controller import Controller
from cocotb_tools.pytest._logging import Logging
from cocotb_tools.pytest._option import (
    Option,
    add_options_to_parser,
    populate_ini_to_options,
)
from cocotb_tools.pytest.hdl import _SIMULATORS, HDL
from cocotb_tools.pytest.mark import _register_markers
from cocotb_tools.runner import Runner, get_runner

_ENTRY_POINT: str = ",".join(
    (
        "cocotb_tools._coverage:start_cocotb_library_coverage",
        "cocotb.logging:_configure",
        "cocotb._init:init_package_from_simulation",
        "cocotb_tools.pytest._init:run_regression",
    )
)
if TYPE_CHECKING:
    from typing import TypeAlias

    TestStatus: TypeAlias = TestShortLogReport | tuple[str, str, str | tuple[str, Mapping[str, bool]]]


def _to_timescale(value: str) -> tuple[str, str]:
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


def _to_dict(items: Iterable[str]) -> dict[str, object]:
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


_OPTIONS: tuple[Option, ...] = (
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
        choices=("auto", *tuple(_SIMULATORS.values())),
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
        "cocotb_toplevel_lang",
        choices=("auto", "verilog", "vhdl"),
        default="auto",
        description="""
            Language of the HDL toplevel module.
            Can be set to notify tests about preferred language in multi-language HDL design.
            This is also used by simulators that support more than one interface
            (:term:`VPI`, :term:`VHPI`, or :term:`FLI`) to select the appropriate interface to start cocotb.
            When set to ``auto``, value will be automatically evaluated based on selected HDL simulator or
            list of HDL source files provided during build stage in :py:meth:`cocotb_tools.pytest.hdl.HDL.build` or
            :py:meth:`cocotb_tools.runner.Runner.build` methods.
        """,
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
        "cocotb_log_level",
        choices=("trace", "debug", "info", "warning", "error", "critical"),
        description="""
            The default log level of all "cocotb" Python loggers. The default is unset, which means that the log
            level is inherited from the root logger. This behaves similarly to :py:const:`logging.NOTSET`.
        """,
    ),
    Option(
        "gpi_log_level",
        choices=("trace", "debug", "info", "warning", "error", "critical"),
        description="""
            The default log level of all "gpi" (the low-level simulator interface) loggers, including both Python
            and the native GPI logger. The default is unset, which means that the log level is inherited from the
            root logger. This behaves similarly to :py:const:`logging.NOTSET`.
        """,
    ),
    Option(
        "pygpi_users",
        nargs="*",
        metavar="MODULE:FUNCTION",
        default=(_ENTRY_POINT,),
        description="""
            The Python module and callable that starts up the Python cosimulation environment. User overloads can be
            used to enter alternative Python frameworks or to hook existing cocotb functionality. It is formatted as
            ``path.to.entry.module:entry_point.function,other_module:other_func``. The string before the colon is the
            Python module to import and the string following the colon is the object to call as the entry function.
            The entry function must be a callable matching this form: ``entry_function(argv: List[str]) -> None``
        """,
    ),
)


def _options_for_documentation() -> ArgumentParser:
    """It helps to attach plugin options into Sphinx documentation using the sphinx-argparse extension."""
    parser: ArgumentParser = ArgumentParser(
        prog="pytest",
        description="Plugin options",
    )

    for option in _OPTIONS:
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


@fixture(scope="session")
def dut() -> SimHandleBase:
    """A cocotb fixture that is providing a simulation handle to DUT.

    Provided simulation handle is the same as :py:data:`cocotb.top`.

    Example usage:

    .. code:: python

        async def test_dut_feature_1(dut) -> None:
            dut.rst.value = 0
            dut.clk.value = 0

            # Testing DUT feature
            ...

    Returns:
        Simulation handle to DUT (equivalent to :py:data:`cocotb.top`).
    """
    return cocotb.top


@fixture(scope="session")
def hdl_session(request: FixtureRequest) -> HDL:
    """A cocotb fixture that is providing a helper instance to define own HDL design and to build it.

    .. note::

        This fixture is scoped to global ``session`` scope.
        It can be useful to build the whole HDL project with different HDL modules at once not per test.

    It contains own instance of :py:class:`~cocotb_tools.runner.Runner` that can be accessed directly
    from :py:attr:`~cocotb_tools.pytest.hdl.HDL.runner` member.

    Defined HDL design can be build by invoking the :py:meth:`~cocotb_tools.pytest.hdl.HDL.build()` method
    from **non-async** test functions. This method will invoke build step from :py:attr:`~cocotb_tools.pytest.hdl.HDL.runner` member.

    Requested fixture will pass various plugin :ref:`options <pytest-plugin-options>`
    to own instance of :py:class:`~cocotb_tools.runner.Runner`. Like setting a desired verbosity level for cocotb runner.

    Please refer to available public members of :py:class:`~cocotb_tools.pytest.hdl.HDL` that can be used to define own HDL design.

    Example usage:

    .. code:: python

        import pytest
        from cocotb_tools.pytest.hdl import HDL


        @pytest.fixture(scope="session")
        def my_hdl_project(hdl_session: HDL) -> HDL:
            # Build whole HDL design with all HDL modules at once
            hdl_session.sources = (
                # Add more HDL source files here
                # ...
                DIR / "my_hdl_module_1.sv",
                DIR / "my_hdl_module_2.sv",
            )

            hdl_session.build()

            return hdl_session


        @pytest.fixture(name="my_hdl_module_1")
        def my_hdl_module_1_fixture(hdl: HDL, my_hdl_project: HDL) -> HDL:
            # Define HDL module 1
            hdl.build_dir = my_hdl_project.build_dir
            hdl.toplevel = "my_hdl_module_1"

            return hdl


        @pytest.fixture(name="my_hdl_module_2")
        def my_hdl_module_2_fixture(hdl: HDL, my_hdl_project: HDL) -> HDL:
            # Define HDL module 2
            hdl.build_dir = my_hdl_project.build_dir
            hdl.toplevel = "my_hdl_module_2"

            return hdl


        @pytest.mark.cocotb_runner
        def test_dut_1(my_hdl_module_1: HDL) -> None:
            # Run HDL simulator with cocotb tests
            my_hdl_module_1.test()


        @pytest.mark.cocotb_runner
        def test_dut_2(my_hdl_module_2: HDL) -> None:
            # Run HDL simulator with cocotb tests
            my_hdl_module_2.test()


    Args:
        request: The pytest fixture request that is providing plugin :ref:`options <pytest-plugin-options>`
                 to this fixture. These options will be used to configure own instance of
                 :py:class:`~cocotb_tools.runner.Runner`.

    Returns:
        Instance that allows to build and test HDL design.
    """
    return request.config.hook.pytest_cocotb_make_hdl(request=request)


@fixture
def hdl(request: FixtureRequest, hdl_session: HDL) -> HDL:
    """A cocotb fixture that is providing a helper instance to define own HDL design, to build it and
    run set of cocotb tests from test modules (testbenches) against selected top level design.

    .. note::

        This fixture is scoped to default ``function`` scope.
        It can help to build HDL module per test and run tests for defined HDL top level.

    It contains own instance of :py:class:`~cocotb_tools.runner.Runner` that can be accessed directly
    from :py:attr:`~cocotb_tools.pytest.hdl.HDL.runner` member.

    Defined HDL design can be build by invoking the :py:meth:`~cocotb_tools.pytest.hdl.HDL.build()` method and
    test by invoking the :py:meth:`~cocotb_tools.pytest.hdl.HDL.test()` method from **non-async** test functions.
    These methods will invoke build and test steps from :py:attr:`~cocotb_tools.pytest.hdl.HDL.runner` member.

    Requested fixture will pass various plugin :ref:`options <pytest-plugin-options>`
    to own instance of :py:class:`~cocotb_tools.runner.Runner`. Like setting a desired verbosity level for cocotb runner.

    Please refer to available public members of :py:class:`~cocotb_tools.pytest.hdl.HDL` that can be used to define own HDL design.

    Example usage:

    .. code:: python

        import pytest
        from cocotb_tools.pytest.hdl import HDL


        @pytest.fixture(name="my_hdl_module")
        def my_hdl_module_fixture(hdl: HDL) -> HDL:
            # Build HDL module per test
            hdl.toplevel = "my_hdl_module"

            hdl.sources = (
                # Add more HDL source files here
                # ...
                DIR / "my_hdl_module.sv",
            )

            hdl.build()

            return hdl


        @pytest.mark.cocotb_runner
        def test_dut(my_hdl_module: HDL) -> None:
            # Run HDL simulator with cocotb tests
            my_hdl_module.test()


    Args:
        request: The pytest fixture request that is providing plugin :ref:`options <pytest-plugin-options>`
                 to this fixture. These options will be used to configure own instance of
                 :py:class:`~cocotb_tools.runner.Runner`.
        hdl_session: HDL design defined at global ``session`` scope level.

    Returns:
        Instance that allows to build and test HDL design.
    """
    instance: HDL = request.config.hook.pytest_cocotb_make_hdl(request=request)

    # Runner in test() method is checking for hdl_toplevel_lang,
    # if missing then it will retrieve this information from list of HDL source files
    # Unfortunately, they are not set in Runner created during function scope when build() was not called
    if not hdl_session.toplevel_lang and hasattr(hdl_session.runner, "_sources"):
        instance.toplevel_lang = hdl_session.runner._check_hdl_toplevel_lang(
            hdl_session.toplevel_lang
        )

    return instance


def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    add_options_to_parser(parser, "cocotb", _OPTIONS)


def pytest_addhooks(pluginmanager: PytestPluginManager) -> None:
    """Called at plugin registration time to add specification of cocotb hooks.

    Args:
        pluginmanager: The pytest plugin manager.
    """
    pluginmanager.add_hookspecs(hookspecs)


@hookimpl(trylast=True)
def pytest_cocotb_make_hdl(request: FixtureRequest) -> HDL:
    """Create new instance of :py:class:`cocotb_tools.pytest.hdl.HDL`.

    Args:
        request: The pytest fixture request object.

    Returns:
        New instance of HDL.
    """
    return HDL(request)


@hookimpl(trylast=True)
def pytest_cocotb_make_runner(simulator_name: str) -> Runner:
    """Create new instance of :py:class:`cocotb_tools.runner.Runner`.

    Args:
        simulator_name: Name of HDL simulator.

    Returns:
        New instance of runner.
    """
    return get_runner(simulator_name)


@hookimpl(tryfirst=True)
def pytest_configure(config: Config) -> None:
    option = config.option

    _register_markers(config)
    populate_ini_to_options(config, _OPTIONS)

    if not option.cocotb_timescale:
        option.cocotb_timescale = None

    elif isinstance(option.cocotb_timescale, str):
        option.cocotb_timescale = _to_timescale(option.cocotb_timescale)

    if isinstance(option.cocotb_env, list):
        option.cocotb_env = _to_dict(option.cocotb_env)

    if isinstance(option.cocotb_defines, list):
        option.cocotb_defines = _to_dict(option.cocotb_defines)

    if isinstance(option.cocotb_parameters, list):
        option.cocotb_parameters = _to_dict(option.cocotb_parameters)

    config.pluginmanager.register(Logging(config), "cocotb_logging")

    if not getattr(cocotb, "is_simulation", False):
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

        if any(
            marker.name in ("cocotb_runner", "cocotb_test") for marker in markers or ()
        ):
            setattr(obj, "__test__", True)

        elif (
            inspect.iscoroutinefunction(obj)
            and "dut" in inspect.signature(obj).parameters
        ):
            marker: Mark = mark.cocotb_test().mark

            if markers is None:
                setattr(obj, "pytestmark", [marker])
            else:
                markers.append(marker)

    return None


def _is_cocotb_test_report(item: Any) -> bool:
    """Check if provided pytest item is cocotb test report.

    Args:
        item: Pytest item (test report).

    Returns:
        True if provided pytest item is cocotb test report. Otherwise False.
    """
    return isinstance(item, TestReport) and getattr(item, "cocotb", False)


@hookimpl(hookwrapper=True, trylast=True)
def pytest_report_teststatus(
    report: CollectReport | TestReport, config: Config
) -> Generator[None, Result[TestStatus], None]:
    result: Result[TestStatus] = yield
    status: TestStatus = result.get_result()

    if (
        isinstance(report, TestReport)
        and ("cocotb_runner" in report.keywords)
        and (report.when == "call")
    ):
        category, letter, word = status
        category = f"{category} cocotb runner"
        if isinstance(word, str):
            word = f"{word} COCOTB RUNNER"
        else:
            word = (f"{word[0]} COCOTB RUNNER", word[1])
        result.force_result(
            TestShortLogReport(category=category, letter=letter, word=word)
        )


@hookimpl(hookwrapper=True, tryfirst=True)
def pytest_terminal_summary(
    terminalreporter: TerminalReporter,
    exitstatus: ExitCode,
    config: Config,
) -> Generator[None]:
    # Print cocotb runner failures before test failures
    terminalreporter.summary_failures_combined(
        which_reports="failed cocotb runner",
        sep_title="COCOTB RUNNER FAILURES",
        style=config.option.tbstyle,
    )
    # Continue with the rest of pytest terminal summary
    yield

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
                if _is_cocotb_test_report(item):
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
