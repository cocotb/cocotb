# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Pytest plugin to integrate pytest with cocotb."""

import inspect
import os
import re
import shlex
from collections.abc import Sequence
from pathlib import Path
from time import time
from typing import Any

from pytest import (
    Class,
    Collector,
    Config,
    ExitCode,
    Function,
    Item,
    Mark,
    Module,
    Parser,
    PytestPluginManager,
    Session,
    TerminalReporter,
    TestReport,
    fixture,
    hookimpl,
    mark,
)

import cocotb
import cocotb.handle
from cocotb._decorators import Parameterized, Test
from cocotb.handle import SimHandleBase
from cocotb_tools.pytest.controller import Controller
from cocotb_tools.pytest.option import Option, add_options_to_parser, is_cocotb_option

ENTRY_POINTS: dict[str, str] = {
    "pytest": "cocotb_tools.pytest._init:run_regression",
    "cocotb": "cocotb._init:run_regression",
}


@fixture(name="dut", scope="session")
def dut_fixture() -> SimHandleBase | None:
    return getattr(cocotb, "top", None)


def pytest_addoption(parser: Parser, pluginmanager: PytestPluginManager) -> None:
    add_options_to_parser(
        parser,
        "cocotb",
        Option(
            "cocotb_regression_manager",
            choices=("pytest", "cocotb", "none"),
            default="pytest",
            help="""
                Regression manager that will be used to run cocotb tests.
                - pytest: Use pytest as regression manager to manage and run cocotb tests.
                - cocotb: Use built-in cocotb regression manager to manage and run cocotb tests.
            """,
        ),
        Option(
            "cocotb_summary",
            action="store_true",
            help="Show cocotb test summary info.",
        ),
        Option(
            "cocotb_sim_time_unit",
            choices=("step", "fs", "ps", "ns", "us", "ms", "sec"),
            default="ns",
            help="Simulation time unit that will be used during tests reporting.",
        ),
        Option(
            "cocotb_gui",
            action="store_true",
            help="Enable the GUI mode in the simulator (if supported).",
        ),
        Option(
            "cocotb_waves",
            action="store_true",
            help="Enable wave traces dump for simulator (if supported).",
        ),
        Option(
            "cocotb_waveform_viewer",
            default="surfer",
            help="""
                The name of the waveform viewer executable to use (like surfer) when GUI mode is enabled for simulators
                that do not have a built-in waveform viewer (like Verilator) The executable name will be called with the
                name of the waveform file as the argument.
            """,
        ),
        Option(
            "cocotb_random_seed",
            default=int(time()),
            default_in_help="current epoch time in seconds",
            help="Seed the Python random module to recreate a previous test stimulus.",
        ),
        Option(
            "cocotb_ansi_output",
            choices=("yes", "no", "auto"),
            default="auto",
            help="""
                Override the default behavior of annotating cocotb output with ANSI color codes if the output is a terminal.
                - yes: Forces output to be ANSI-colored regardless of the type of stdout or the presence of NO_COLOR.
                - no:  Suppresses the ANSI color output in the log messages.
            """,
        ),
        Option(
            "cocotb_attach",
            default=0,
            help="""
                Pause time value in seconds before the simulator start. If set to non-zero value, cocotb will print the
                process ID (PID) to attach to and wait the specified time in seconds before actually letting the
                simulator run.
            """,
        ),
        Option(
            "cocotb_enable_profiling",
            action="store_true",
            help="""
                Enable performance analysis of the Python portion of cocotb. When enabled, a file test_profile.pstat
                will be written which contains statistics about the cumulative time spent in the functions. From this,
                a callgraph diagram can be generated with gprof2dot and graphviz.
            """,
        ),
        Option(
            "cocotb_indexing_changed_warning",
            action="store_true",
            help="""
                Enable to cause a warning to be emitted on all LogicArray and Array indexing and slicing operations if
                the indexing would have changed between cocotb 1.x and 2.x.
            """,
        ),
        Option(
            "cocotb_log_level",
            choices=("trace", "debug", "info", "warning", "error", "critical"),
            help="""
                The default log level of all "cocotb" Python loggers. The default is unset, which means that the log
                level is inherited from the root logger. This behaves similarly to INFO.
            """,
        ),
        Option(
            "cocotb_log_prefix",
            metavar="FORMAT",
            help="""
                Customize the log message prefix. The value of this variable should be in Python f-string syntax.
                It has access to the following variables:
                - record:  The LogRecord being formatted. This includes the attribute created_sim_time, which is the simulation time in steps.
                - time:    The Python time module.
                - simtime: The cocotb cocotb.simtime module.
                - ANSI:    The cocotb cocotb.logging.ANSI enum, which contains ANSI escape codes for coloring the output.
            """,
        ),
        Option(
            "cocotb_pdb_on_exception",
            action="store_true",
            help="""
                If enabled, cocotb will drop into the Python debugger (pdb) if a test fails with an exception.
                See also the Python subsection of Attaching a Debugger.
            """,
        ),
        Option(
            "cocotb_plusargs",
            nargs="*",
            help="""
                Plusargs are options that are starting with a plus (+) sign.  They are passed to the simulator and are
                also available within cocotb as cocotb.plusargs. In the simulator, they can be read by the
                Verilog/SystemVerilog system functions $test$plusargs and $value$plusargs.
            """,
        ),
        Option(
            "cocotb_reduced_log_fmt",
            choices=("yes", "no"),
            default="yes",
            help="""
                - yes: Logs will include simulation time, message type (INFO, WARNING, ERROR, ...), logger name, and the log message itself.
                - no:  The filename and line number where a log function was called will be added between the logger name and the log message.
            """,
        ),
        Option(
            "cocotb_resolve_x",
            choices=("error", "weak", "zeros", "ones", "random"),
            help="""
                Defines how to resolve bits with a value of X, Z, U, W, or - when being converted to integer. Valid settings are:
                - error:  Resolves nothing.
                - weak:   Resolves L to 0 and H to 1.
                - zeros:  Like weak, but resolves all other non-0/1 values to 0.
                - ones:   Like weak, but resolves all other non-0/1 values to 1.
                - random: Like weak, but resolves all other non-0/1 values randomly to either 0 or 1.
                There is also a slight difference in behavior of bool(logic).
                When this is set, bool(logic) treats all non-0/1 values as equivalent to 0.
                When this is not set, bool(logic) will fail on non-0/1 values.
                Warning: Using this feature is not recommended.
            """,
        ),
        Option(
            "cocotb_results_file",
            default=Path("results.xml"),
            help="The file name where xUnit XML tests results are stored.",
        ),
        Option(
            "cocotb_rewrite_assertion_files",
            default="*.py",
            help="""
                Select the Python files to apply pytest’s assertion rewriting to. This is useful to get more
                informative assertion error messages in cocotb tests. Specify using a space-separated list of file
                globs, e.g. test_*.py testbench_common/**/*.py. Set to the empty string to disable assertion rewriting.
            """,
        ),
        Option(
            "cocotb_scheduler_debug",
            action="store_true",
            help="""
                Enable additional log output of the coroutine scheduler. This will default the value of debug, which
                can later be modified.
            """,
        ),
        Option(
            "cocotb_test_filter",
            metavar="REGEXP",
            nargs="*",
            help="""
                A regular expression matching names of test function(s) to run. If this is not defined, cocotb
                discovers and executes all functions decorated with the @cocotb.test or @pytest.mark.cocotb decorator in
                the supplied --cocotb-test-modules list.
            """,
        ),
        Option(
            "cocotb_test_modules",
            nargs="*",
            help="""
                The name of the Python module(s) to search for test functions - if your tests are in a file called
                test_mydesign.py, --cocotb-test-modules would be set to test_mydesign. All tests will be run from each
                specified module in order of the module’s appearance in this list.
            """,
        ),
        Option(
            "cocotb_testcase",
            nargs="*",
            help="A list of tests to run. Does an exact match on the test name.",
        ),
        Option(
            "cocotb_toplevel",
            help="""
                Use this to indicate the instance in the hierarchy to use as the DUT. If this isn’t defined then the
                first root instance is used. Leading and trailing whitespace are automatically discarded. The DUT is
                available in cocotb tests as a Python object at cocotb.top; and is also passed to all cocotb tests as
                the first and only parameter.
            """,
        ),
        Option(
            "cocotb_trust_inertial_writes",
            action="store_true",
            help="""
                It enables a mode which allows cocotb to trust that VPI/VHPI/FLI inertial writes are applied properly
                according to the respective standards. This mode can lead to noticeable performance improvements, and
                also includes some behavioral difference that are considered by the cocotb maintainers to be “better”.
                Not all simulators handle inertial writes properly, so use with caution. This is achieved by not
                scheduling writes to occur at the beginning of the ReadWrite mode, but instead trusting that the
                simulator’s inertial write mechanism is correct. This allows cocotb to avoid a VPI callback into Python
                to apply writes.
            """,
        ),
        Option(
            "cocotb_user_coverage",
            action="store_true",
            help="""
                Enable to collect Python coverage data for user code. For some simulators, this will also report HDL
                coverage. If coverage configuration file doesn't exist, branch coverage is collected and files in the
                cocotb package directory are excluded. This needs the coverage Python module to be installed.
            """,
        ),
        Option(
            "cocotb_pytest_args",
            default_in_help="passing arguments as-is from main pytest to subprocess pytest",
            help="""
                Override command line arguments for pytest used as regression manager (subprocess).
                By default, it will use the same arguments as main pytest (parent process).
                Example: pytest --capture=no -v --cocotb-pytest-args='--capture=fd -vv -rA'
            """,
        ),
        Option(
            "cocotb_pytest_dir",
            default_in_help="current working directory",
            metavar="PATH",
            help="Override path from where pytest was invoked.",
        ),
        Option(
            "gpi_log_level",
            choices=("trace", "debug", "info", "warning", "error", "critical"),
            help="""
                The default log level of all "gpi" (the low-level simulator interface) loggers, including both Python
                and the native GPI logger. The default is unset, which means that the log level is inherited from the
                root logger. This behaves similarly to INFO.
            """,
        ),
        Option(
            "gpi_extra",
            nargs="*",
            metavar="LIBRARY:FUNCTION",
            help="""
                List of extra libraries that are dynamically loaded at runtime. A function from each of these libraries
                will be called as an entry point prior to elaboration, allowing these libraries to register system
                functions and callbacks. Note that HDL objects cannot be accessed at this time. An entry point function
                must be named following a : separator, which follows an existing simulator convention.
                For example: --gpi-extra libnameA.so:entryA libnameB.so:entryB will first load libnameA.so with entry
                point entryA, then load libnameB.so with entry point entryB.
            """,
        ),
        Option(
            "pygpi_python_bin",
            help="""
                The Python binary in the Python environment to use with cocotb. This is set to the result of
                cocotb-config --python-bin in the Makefiles and Python Runner. You will likely only need to set this
                manually if you are using a Python environment other than the currently activated environment, or if you
                are using a custom flow.
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
            help="""
                The Python module and callable that starts up the Python cosimulation environment. User overloads can be
                used to enter alternative Python frameworks or to hook existing cocotb functionality. It is formatted as
                path.to.entry.module:entry_point.function,other_module:other_func. The string before the colon is the
                Python module to import and the string following the colon is the object to call as the entry function.
                The entry function must be a callable matching this form: entry_function(argv: List[str]) -> None
            """,
        ),
    )


@hookimpl(tryfirst=True)
def pytest_configure(config: Config) -> None:
    option = config.option

    config.addinivalue_line(
        "markers",
        "cocotb: mark coroutine function as cocotb test and normal function as cocotb runner",
    )

    if option.pygpi_users is None:
        option.pygpi_users = config.getini("pygpi_users")

    if option.cocotb_regression_manager is None:
        option.cocotb_regression_manager = config.getini("cocotb_regression_manager")

    entry_point: str | None = ENTRY_POINTS.get(option.cocotb_regression_manager)

    if entry_point and entry_point not in option.pygpi_users:
        option.pygpi_users.append(entry_point)

    for name, optval in vars(option).items():
        if is_cocotb_option(name):
            value: Any = optval

            if value is None:
                value = config.getini(name)
                setattr(option, name, value)

            environment: str = name.upper()

            if value in (True, "yes"):
                os.environ[environment] = "1"
            elif value in (False, "no", "none", "auto", "", []):
                if environment in os.environ:
                    del os.environ[environment]
            elif isinstance(value, list):
                os.environ[environment] = ",".join(value)
            else:
                os.environ[environment] = str(value)

    os.environ["COCOTB_PYTEST_DIR"] = (
        str(Path(option.cocotb_pytest_dir).resolve())
        if option.cocotb_pytest_dir
        else str(config.invocation_params.dir)
    )

    os.environ["COCOTB_PYTEST_ARGS"] = (
        option.cocotb_pytest_args
        if option.cocotb_pytest_args
        else shlex.join(config.invocation_params.args)
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


def _unwrap_obj(obj: object, markers: list[Mark] | None = None) -> object:
    if markers is None:
        markers = []

    if isinstance(obj, Parameterized):
        # Create dictionary of named arguments with values defined for function parametrization
        # @cocotb.parametrize(x=[1, 2], y=[3, 4]) -> {"x": [1, 2], "y": [3, 4]}
        args: dict[str, list[Any]] = {}

        for names, values in obj.options:
            if isinstance(names, str):
                args.setdefault(names, []).extend(values)
            else:
                for index, name in enumerate(names):
                    items: Any = values[index] if index < len(values) else None

                    if isinstance(items, Sequence):
                        args.setdefault(name, []).extend(items)

        # Replace @cocotb.parametrize(...) decorator with equivalent @pytest.mark.parametrize(...) markers
        # @cocotb.parametrize(x=[1, 2], y=[3, 4])
        # vvv
        # @pytest.parametrize("x", [1, 2])
        # @pytest.parametrize("y", [3, 4])
        markers.extend(
            mark.parametrize(arg, values).mark for arg, values in args.items()
        )
        markers.append(mark.cocotb().mark)

        # Process cocotb Test from cocotb Parameterized
        return _unwrap_obj(obj.test_template.func, markers)

    if isinstance(obj, Test):
        # Concate pytest markers from Test object and test function
        # Replace @cocotb.test decorator with @pytest.mark.cocotb marker
        #
        # @pytest.mark.<name1>
        # @cocotb.test(...) -> @pytest.mark.cocotb(...)
        # @cocotb.mark.<name2>
        # async def func(dut) -> None:
        kwargs: dict[str, Any] = {}

        for name, value in vars(obj).items():
            if not name.startswith("_") and name != "func":
                kwargs[name] = value

        markers.append(mark.cocotb(**kwargs).mark)

        return _unwrap_obj(obj.func, markers)

    if not getattr(obj, "__test__", False):
        markers.extend(getattr(obj, "pytestmark", ()))
        setattr(obj, "pytestmark", markers)
        setattr(obj, "__test__", True)

    # Process cocotb test function from cocotb Test
    return obj


@hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(
    collector: Module | Class, name: str, obj: object
) -> None | Item | Collector | list[Item | Collector]:
    if isinstance(obj, (Parameterized, Test)):
        obj = _unwrap_obj(obj)

        setattr(collector.obj, name, obj)

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


@hookimpl(tryfirst=True)
def pytest_collection_modifyitems(
    session: Session, config: Config, items: list[Item]
) -> None:
    testcases: list[str] = config.option.cocotb_testcase
    filters: list[re.Pattern] = list(map(re.compile, config.option.cocotb_test_filter))

    if not testcases and not filters:
        return

    selected_items: list[Item] = []
    deselected_items: list[Item] = []

    for item in items:
        if (
            not is_cocotb_test(item)
            or item.name in testcases
            or any(pattern.search(item.name) for pattern in filters)
        ):
            selected_items.append(item)
        else:
            deselected_items.append(item)

    items[:] = selected_items
    config.hook.pytest_deselected(items=deselected_items)


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

                    for index, width in enumerate(widths):
                        widths[index] = max(width, len(summary[index][-1]))

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
