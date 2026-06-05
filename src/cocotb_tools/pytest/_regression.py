# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Pytest regression manager for cocotb.

This module integrates cocotb with pytest, allowing pytest to collect, configure, run, and report on cocotb simulation tests.
"""

from __future__ import annotations

import bdb
import hashlib
import random
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Generator, Iterable
from functools import wraps
from importlib import import_module
from inspect import isasyncgenfunction, iscoroutinefunction
from logging import Logger, getLogger
from multiprocessing.connection import Client
from pathlib import Path
from time import sleep, time
from typing import Any, Callable, Literal, cast

from _pytest.config import default_plugins
from _pytest.logging import LoggingPlugin
from _pytest.outcomes import Exit, Skipped
from pytest import (
    CallInfo,
    Class,
    Collector,
    CollectReport,
    Config,
    ExceptionInfo,
    ExitCode,
    FixtureDef,
    Function,
    Item,
    Mark,
    Module,
    PytestPluginManager,
    Session,
    TestReport,
    hookimpl,
)

import cocotb
import cocotb._shutdown
import cocotb._test_manager
import cocotb.simulator
import cocotb.types._resolve
from cocotb._decorators import Test, TestGenerator
from cocotb._extended_awaitables import with_timeout
from cocotb._gpi_triggers import Timer
from cocotb._test_manager import TestManager
from cocotb.handle import SimHandleBase
from cocotb.simtime import TimeUnit, get_sim_time
from cocotb_tools.pytest._collector import is_dut_fixture
from cocotb_tools.pytest._fixture import (
    AsyncFixtureCachedResult,
    resolve_fixture_arg,
)
from cocotb_tools.pytest._test import RunningTestSetup
from cocotb_tools.pytest._utils import to_list

RETRIES: int = 10
INTERVAL: float = 0.1  # seconds

AsyncFunction = Callable[..., Awaitable]
When = Literal["setup", "call", "teardown"]
"""Test phase."""


class SimFailure(BaseException):
    """An exception raised when a test fails due to simulator failure.

    This is used internally to signal that the simulator ended or failed unexpectedly during a test run.
    """


def finish_on_exception(method: Callable[..., Any]) -> Callable[..., Any]:
    """A decorator that wraps a regression manager method to handle exceptions.

    It catches any raised `BaseException`, notifies pytest and its plugins about the exception, and terminates the simulator session.
    """

    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            return method(self, *args, **kwargs)
        except BaseException:
            # Notify pytest and plugins about exception. Finish pytest and simulation
            self._notify_exception(ExceptionInfo.from_current())
            self._finish()

    return wrapper


class RegressionManager:
    """The regression manager for running cocotb tests via pytest.

    This class acts as a pytest plugin within the simulation process.
    It manages the pytest session, intercepts item collection, sets up fixtures (including coroutine fixtures),
    schedules test execution on the cocotb scheduler, and forwards test reports to the main pytest process.
    """

    _timer1 = Timer(1)

    def __init__(
        self,
        *args: str,
        nodeid: str = "",
        toplevel: str = "",
        reporter_address: str = "",
        xmlpath: str | None = None,
        keywords: Iterable[str] | None = None,
        test_modules: Iterable[str] | None = None,
        invocation_dir: Path | str | None = None,
        seed: int | None = None,
        relative_to: Path | str | None = None,
        attachments: Iterable[Path | str] | None = None,
    ) -> None:
        """Initialize a new regression manager instance for cocotb tests.

        Args:
            *args: Command line arguments for pytest.
            nodeid: Node identifier of the simulation process.
            toplevel: Name of the HDL top-level design.
            xmlpath: Path to write the JUnit XML report, overriding the default ``--junit-xml`` option.
            keywords: List of additional keywords for filtering cocotb tests.
            test_modules: List of test modules (Python modules with cocotb tests) to be loaded.
            invocation_dir: Path to the directory from which pytest was originally invoked.
            reporter_address: IPC address (Unix socket, Windows pipe, TCP, etc.) of the test reporter.
            seed: Initialization value for the random number generator. If not provided, the current timestamp is used.
            relative_to: If provided, absolute paths in reports are converted to be relative to this path.
            attachments: List of file attachments to be included in the test reports.
        """
        self._toplevel: str = toplevel
        """Name of the top-level HDL design."""

        self._test: Test | TestGenerator
        """The currently executing cocotb test object."""

        self._running_test: TestManager
        """The test manager for the currently active phase ("setup", "call", or "teardown")."""

        self._setups: deque[TestManager] = deque[TestManager]()
        """Queue of test setups collected from the :func:`pytest.hookspec.pytest_fixture_setup` hook."""

        self._call: TestManager | None = None
        """The test call manager created in the :func:`pytest.hookspec.pytest_runtest_call` hook, or ``None``."""

        self._teardowns: deque[TestManager] = deque[TestManager]()
        """Queue of test teardowns registered via setup finalizers using the
        :meth:`pytest.FixtureRequest.addfinalizer` method.
        """

        if nodeid.startswith("::cocotb::") and nodeid.endswith("::simulation"):
            nodeid = nodeid.removesuffix("simulation")
        else:
            nodeid += "::"

        self._scheduled: bool = False
        self._index: int = 0
        self._finished: bool = False
        self._call_start: float | None = None
        self._sim_time_start: float = 0
        self._sim_time_unit: TimeUnit = "step"
        self._nodeid: str = nodeid
        self._keywords: list[str] = list(keywords) if keywords else []
        self._reporter_address: str = reporter_address
        self._logging_plugin: LoggingPlugin | None = None
        self._logging_root_level: int = getLogger().level
        self._logging_level: int = 0
        self._logging_restored: bool = False
        self._seed: int = int(time()) if seed is None else seed
        self._random_state: Any = random.getstate()
        self._random_x_resolver_state: Any = (
            cocotb.types._resolve._randomResolveRng.getstate()
        )
        relative_to_path = relative_to or invocation_dir
        self._relative_to: Path = (
            Path(relative_to_path).resolve() if relative_to_path else Path.cwd()
        )
        self._attachments: list[Path] = self._normalize_paths(attachments)

        pluginmanager = PytestPluginManager()

        # Initialize configuration object needed for pytest
        config: Config = Config(
            pluginmanager,
            invocation_params=Config.InvocationParams(
                args=args,
                plugins=None,
                dir=Path(invocation_dir) if invocation_dir else Path.cwd(),
            ),
        )

        if args:
            # Handle any "-p no:plugin" args.
            pluginmanager.consider_preparse(args, exclude_only=True)

        for plugin in default_plugins:
            pluginmanager.import_plugin(plugin)

        # Register itself as plugin
        config.pluginmanager.register(self, name="cocotb_regression_manager")

        # Parse pytest command line arguments, including from PYTEST_ADDOPTS environment variable
        config = config.pluginmanager.hook.pytest_cmdline_parse(
            pluginmanager=config.pluginmanager, args=list(args)
        )

        # Get log file option from command line or from configuration file(s)
        log_file: str | None = config.getoption("log_file") or config.getini("log_file")

        # Unify it to current working directory where simulation process is running to avoid overriding it
        if log_file:
            config.option.log_file = Path(log_file).name

        if xmlpath:
            config.option.xmlpath = xmlpath

        if test_modules:
            # https://github.com/pytest-dev/pytest/issues/1596
            # We cannot use --pyargs to load Python modules directly because conftest.py will be not loaded
            config.option.pyargs = False
            config.args = [
                str(import_module(test_module).__file__) for test_module in test_modules
            ]

        # Create session context for tests
        self._session: Session = Session.from_config(config)
        self._session.exitstatus = ExitCode.OK  # this is unset in pytest by default

        # Call all pytest_configure hooks from registered plugins to configure config object
        self._session.config._do_configure()

    @finish_on_exception
    def start_regression(self) -> None:
        """Start the pytest regression run.

        This triggers the pytest lifecycle hooks: session start, collection, and the test loop.
        """
        self._session.config.hook.pytest_sessionstart(session=self._session)
        self._session.config.hook.pytest_collection(session=self._session)
        self._session.config.hook.pytest_runtestloop(session=self._session)

    @hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: Session) -> None:
        """Retrieve the logging plugin after the pytest Session object is created.

        This is called before performing collection and entering the runtest loop.

        Args:
            session: The active pytest Session object.
        """
        self._logging_plugin = session.config.pluginmanager.get_plugin("logging-plugin")

    @hookimpl(tryfirst=True)
    def pytest_report_header(self, config: Config, start_path: Path) -> str | list[str]:
        """Return header information about cocotb and the simulator for terminal reporting.

        Args:
            config: The pytest config object.
            start_path: The starting directory path.

        Returns:
            A list of strings containing simulator name/version, cocotb version, random seed, and top-level design name.
        """
        return [
            f"Running on {cocotb.SIM_NAME} version {cocotb.SIM_VERSION}",
            f"Initialized cocotb v{cocotb.__version__} from {Path(__file__).parent.resolve()}",
            f"Seeding Python random module with {self._seed}",
            f"Top level set to {self._toplevel!r}",
        ]

    @hookimpl(wrapper=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> Generator[
        None,
        None | Item | Collector | list[Item | Collector],
        None | Item | Collector | list[Item | Collector],
    ]:
        """Intercept pytest item collection to extract and wrap cocotb tests.

        Args:
            collector: The pytest Module or Class collector.
            name: The name of the python object within the collector.
            obj: The python object to collect.

        Yields:
            None.

        Returns:
            The collected and processed test item(s).
        """
        items: None | Item | Collector | list[Item | Collector] = yield

        if items is not None:
            items = list(self.collect_items(to_list(items)))

        return items

    def collect_items(
        self, items: Iterable[Item | Collector]
    ) -> Generator[Item | Collector, None, None]:
        """Filter and collect cocotb test coroutines.

        This filters the collected items, updating any that are coroutines to be recognized
        as cocotb tests and resolving their DUT fixtures.

        Args:
            items: An iterable of collected pytest items or collectors.

        Yields:
            Each collected and updated test item.
        """
        for item in items:
            if isinstance(item, Function) and iscoroutinefunction(item.function):
                self.update_item(item)
                yield item

    def update_item(self, item: Function) -> None:
        """Configure a collected pytest function item to run as a cocotb test.

        This adds the required cocotb markers, updates the node ID to match the
        simulation path, and replaces any DUT fixtures with simulation handles
        pointing to the top-level simulator handle (`cocotb.top`).

        Args:
            item: The pytest Function item to update.
        """
        nodeid: str = self._nodeid
        module: Module | None = item.getparent(Module)

        if module:
            test_module: str = module.getmodpath(includemodule=True)
            item.extra_keyword_matches.update(
                (test_module, f"{test_module}.{item.name}")
            )
            nodeid += test_module

        nodeid += f".{item.name}"

        item._nodeid = nodeid
        item.add_marker("cocotb")
        item.add_marker("cocotb_test")
        item.extra_keyword_matches.update(self._keywords)

        # Replace defined DUT fixtures with the simulation handle :data:`cocotb.top`
        for name, fixturedefs in item._fixtureinfo.name2fixturedefs.items():
            if fixturedefs and (name in "dut" or is_dut_fixture(fixturedefs[-1])):
                fixturedef: FixtureDef = fixturedefs[-1]
                func = fixturedef.func

                if not iscoroutinefunction(func) and not isasyncgenfunction(func):
                    fixturedef.func = cocotb_top  # type: ignore
                    fixturedef.argnames = ()  # type: ignore
                    fixturedef.cached_result = (cocotb.top, None, None)
                    item._fixtureinfo.name2fixturedefs[name] = (fixturedef,)

    @hookimpl(tryfirst=True)
    def pytest_runtestloop(self, session: Session) -> bool:
        """Run the pytest test loop for the collected cocotb test items.

        Args:
            session: The active pytest Session object.

        Returns:
            Always returns True to signal that the loop has been handled.
        """
        if (
            session.testsfailed
            and not session.config.option.continue_on_collection_errors
        ):
            raise session.Interrupted(
                f"{session.testsfailed} error{'s' if session.testsfailed != 1 else ''} during collection"
            )

        if not session.config.option.collectonly and session.items:
            item, nextitem = self._get_item()
            item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
        else:
            self._finish()

        return True

    @hookimpl(tryfirst=True)
    def pytest_runtest_protocol(self, item: Item, nextitem: Item | None) -> bool:
        """Execute the pytest runtest protocol for a single test item.

        This starts the test logging lifecycle and kicks off the test setup.

        Args:
            item: The test item to run.
            nextitem: The next scheduled test item, or ``None`` if this is the last test.

        Returns:
            Always returns True to indicate that the protocol is handled.
        """
        item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
        self._setup(item=item, nextitem=nextitem)

        return True

    @property
    def _item(self) -> Item:
        """The current pytest Item instance being executed."""
        return self._session.items[self._index]

    @property
    def _nextitem(self) -> Item | None:
        """The next pytest Item instance in the session queue, or ``None``."""
        index: int = self._index + 1

        return self._session.items[index] if index < len(self._session.items) else None

    def _call_and_report(
        self,
        item: Item,
        when: When,
        func: Callable[..., None] | None = None,
        **kwargs: object,
    ) -> TestReport:
        """Run a test phase (setup, call, or teardown) and generate a test report.

        Args:
            item: The pytest test Item.
            when: The current phase ("setup", "call", or "teardown").
            func: The callable to execute. If not provided, invokes the default pytest hook for the phase.
            **kwargs: Additional keyword arguments passed to `func`.

        Returns:
            A :class:`pytest.TestReport` object representing the outcome of the phase.
        """
        if not func:
            self._logging_root_level = getLogger().level
            func = getattr(item.ihook, f"pytest_runtest_{when}")
            kwargs["item"] = item
            self._call_start = None

        reraise: tuple[type[BaseException], ...] = (Exit,)

        if not item.config.getoption("usepdb", False):
            reraise += (KeyboardInterrupt,)

        call: CallInfo = CallInfo.from_call(
            lambda: func(**kwargs),
            when=when,
            reraise=reraise,
        )

        if self._call_start is None:
            self._call_start = call.start
            self._sim_time_unit = self._session.config.option.cocotb_sim_time_unit
            self._sim_time_start = get_sim_time(self._sim_time_unit)
        else:
            call.start = self._call_start
            call.duration = call.stop - call.start

        report: TestReport = item.ihook.pytest_runtest_makereport(item=item, call=call)

        if _check_interactive_exception(call, report):
            _interactive_exception(item, call, report)

        return report

    def _completed(self, item: Item, when: When) -> TestReport:
        """Handle the completion of a test phase.

        Updates the report log sections and generates the final test report for the phase.

        Args:
            item: The pytest test Item.
            when: The finished phase ("setup", "call", or "teardown").

        Returns:
            A :class:`pytest.TestReport` object for the completed phase.
        """
        self._update_report_section(item=item, when=when)

        return self._call_and_report(
            item=item, when=when, func=self._running_test.result
        )

    @finish_on_exception
    def _setup_completed(self) -> None:
        """Callback executed when the test setup phase is complete."""
        item: Item = self._item
        nextitem: Item | None = self._nextitem

        report: TestReport = self._completed(item=item, when="setup")
        self._setup(item=item, nextitem=nextitem, report=report)

    def _setup(
        self, item: Item, nextitem: Item | None = None, report: TestReport | None = None
    ) -> None:
        """Execute the setup phase and subsequent test execution phases.

        This runs each collected fixture setup coroutine sequentially. Once all
        fixtures are set up successfully, it proceeds to call the test function itself.
        If any setup fails, it skips to teardown.

        Args:
            item: The pytest test Item.
            nextitem: The next test Item in the queue, or ``None``.
            report: An optional pre-computed test report for the current setup step.
        """
        if not report:
            self._setups.clear()
            report = self._call_and_report(item=item, when="setup")

        if not report.passed:
            item.ihook.pytest_runtest_logreport(report=report)
            self._teardown(item=item, nextitem=nextitem)
            return

        if self._setups:
            self._start(self._setups.popleft())
            return

        item.ihook.pytest_runtest_logreport(report=report)

        self._call = None
        report = self._call_and_report(item=item, when="call")

        if self._call:
            self._start(self._call)
        else:
            item.ihook.pytest_runtest_logreport(report=report)
            self._teardown(item=item, nextitem=nextitem)

    @finish_on_exception
    def _call_completed(self) -> None:
        """Callback executed when the main test function execution phase is complete."""
        item: Item = self._item
        nextitem: Item | None = self._nextitem

        report: TestReport = self._completed(item=item, when="call")
        item.ihook.pytest_runtest_logreport(report=report)
        self._teardown(item=item, nextitem=nextitem)

    @finish_on_exception
    def _teardown_completed(self) -> None:
        """Callback executed when a test teardown finalizer phase is complete."""
        item: Item = self._item
        nextitem: Item | None = self._nextitem

        report: TestReport = self._completed(item=item, when="teardown")
        self._teardown(item=item, nextitem=nextitem, report=report)

    def _teardown(
        self, item: Item, nextitem: Item | None = None, report: TestReport | None = None
    ) -> None:
        """Execute the teardown phase for a test item.

        This runs registered finalizer and teardown coroutines sequentially. After
        completing teardown, it advances the test runner to the next test item.

        Args:
            item: The pytest test Item.
            nextitem: The next test Item in the queue, or ``None``.
            report: An optional pre-computed test report for the current teardown step.
        """
        if not report:
            self._teardowns.clear()
            report = self._call_and_report(
                item=item, when="teardown", nextitem=nextitem
            )

        if self._teardowns:
            self._start(self._teardowns.popleft())
            return

        item.ihook.pytest_runtest_logreport(report=report)
        item.ihook.pytest_runtest_logfinish(nodeid=item.nodeid, location=item.location)

        if nextitem:
            item, nextitem = self._pop_item()
            item.config.hook.pytest_runtest_protocol(item=item, nextitem=nextitem)
        else:
            self._finish()

    def _get_item(self) -> tuple[Item, Item | None]:
        """Get the current and next pytest items."""
        return self._item, self._nextitem

    def _pop_item(self) -> tuple[Item, Item | None]:
        """Advance to the next test item and return the new current and next items."""
        self._index += 1

        return self._get_item()

    def _notify_exception(self, excinfo: ExceptionInfo) -> None:
        """Notify pytest and its plugins about an exception, setting the session exit status."""
        self._session.exitstatus = ExitCode.INTERNAL_ERROR
        self._session.config.notify_exception(excinfo, self._session.config.option)

    def _finish(self) -> None:
        """Finalize the pytest session and terminate the simulator.

        This invokes the session finish hooks, unconfigures pytest, and stops the simulator.
        """
        if self._finished:  # this method must be called once
            return

        self._finished = True

        self._session.config.hook.pytest_sessionfinish(
            session=self._session,
            exitstatus=self._session.exitstatus,
        )

        self._session.config._ensure_unconfigure()
        self._shutdown()

    @hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: Item) -> None:
        """Perform the setup phase for a test item.

        This saves the current logging state and initializes the random seed based
        on the test node ID and the master seed to ensure reproducible runs.

        Args:
            item: The pytest test Item.
        """
        self._save_logging_state()

        # seed random number generator based on test module, name, and COCOTB_RANDOM_SEED
        hasher = hashlib.sha1()
        hasher.update(item.nodeid.encode())
        seed: int = self._seed + int(hasher.hexdigest(), 16)

        # seed random number generators with test seed
        self._random_state = random.getstate()
        random.seed(seed)
        self._random_x_resolver_state = (
            cocotb.types._resolve._randomResolveRng.getstate()
        )
        cocotb.types._resolve._randomResolveRng.seed(seed)
        cocotb.RANDOM_SEED = seed

    @hookimpl(tryfirst=True)
    def pytest_runtest_call(self, item: Item) -> None:
        """Run the actual test code for a test item.

        Saves the current logging state before starting.

        Args:
            item: The pytest test Item.
        """
        self._save_logging_state()

    @hookimpl(tryfirst=True)
    def pytest_runtest_teardown(self, item: Item, nextitem: Item | None = None) -> None:
        """Perform the teardown phase for a test item.

        This restores the logging state and resets the random seed generators
        back to their initial values.

        Args:
            item: The pytest test Item.
            nextitem: The next scheduled test Item, or ``None``.
        """
        self._save_logging_state()

        # Restore random seed to original value
        cocotb.RANDOM_SEED = self._seed
        random.setstate(self._random_state)
        cocotb.types._resolve._randomResolveRng.setstate(self._random_x_resolver_state)

    @hookimpl(tryfirst=True)
    def pytest_fixture_setup(
        self,
        fixturedef: FixtureDef[Any],
        request: Any,  # NOTE: type not available in public pytest API
    ) -> object | None:
        """Execute the setup phase for a fixture.

        If the fixture function is an asynchronous generator or a coroutine,
        it wraps and schedules it via cocotb's test manager. Otherwise, it allows
        pytest to perform the standard synchronous fixture setup.

        Args:
            fixturedef: The fixture definition.
            request: The fixture request.

        Returns:
            ``True`` if the fixture is asynchronous and handled by cocotb, otherwise ``None``.
        """
        fixturefunc = fixturedef.func
        is_coroutine: bool = iscoroutinefunction(fixturefunc)
        is_async_generator: bool = isasyncgenfunction(fixturefunc)

        if not is_coroutine and not is_async_generator:
            return None

        func: Callable[[], Any]
        setup: TestManager

        if is_async_generator:
            # Test setup with teardown, re-assign added sub-tasks during setup to teardown
            func = self._setup_async_generator(fixturedef, request)
        else:
            # Test setup-only without teardown
            func = self._setup_async_function(fixturedef, request)

        if is_async_generator:
            # Test setup with teardown, added sub-tasks during setup will be cancelled by test teardown
            setup = RunningTestSetup(
                func(),
                name=f"Setup {request.fixturename}",
                test_complete_cb=self._setup_completed,
            )
        else:
            # Test setup-only without teardown, run all tasks only during test setup
            setup = TestManager(
                func(),
                name=f"Setup {request.fixturename}",
                test_complete_cb=self._setup_completed,
            )

        cache_key = fixturedef.cache_key(request)
        fixturedef.cached_result = AsyncFixtureCachedResult((setup, cache_key, None))  # type: ignore[assignment]

        self._setups.append(setup)

        return True

    def _setup_async_generator(
        self,
        fixturedef: FixtureDef[Any],
        request: Any,
    ) -> Callable[[], Any]:
        """Wrap an asynchronous generator fixture for setup and teardown.

        Args:
            fixturedef: The fixture definition.
            request: The fixture request.

        Returns:
            A callable that runs the setup portion of the async generator and registers its finalizer.
        """

        async def func() -> Any:
            self._restore_logging_state()

            kwargs: dict[str, Any] = {
                argname: resolve_fixture_arg(request.getfixturevalue(argname))
                for argname in fixturedef.argnames
            }

            iterator: AsyncGenerator[Any, None] = cast(
                "AsyncGenerator", fixturedef.func(**kwargs)
            )

            result = await iterator.__anext__()
            self._add_teardown(fixturedef, request, iterator)

            return result

        return func

    def _setup_async_function(
        self, fixturedef: FixtureDef[Any], request: Any
    ) -> Callable[[], Any]:
        """Wrap a coroutine fixture (setup-only, no teardown).

        Args:
            fixturedef: The fixture definition.
            request: The fixture request.

        Returns:
            A callable that resolves fixture arguments and runs the coroutine fixture.
        """

        async def func() -> Any:
            self._restore_logging_state()

            kwargs: dict[str, Any] = {
                argname: resolve_fixture_arg(request.getfixturevalue(argname))
                for argname in fixturedef.argnames
            }

            return await cast("AsyncFunction", fixturedef.func)(**kwargs)

        return func

    @hookimpl(tryfirst=True)
    def pytest_pyfunc_call(self, pyfuncitem: Function) -> object | None:
        """Execute the test function.

        Wraps the test coroutine, resolves any fixture arguments, handles timeouts
        if specified, and schedules the test execution using cocotb's test manager.

        Args:
            pyfuncitem: The pytest Function test item.

        Returns:
            ``True`` to indicate the call has been handled.
        """
        testfunction = pyfuncitem.obj
        self._test = cocotb.test(testfunction)
        self._test.name = pyfuncitem.name

        timeout: tuple[float, TimeUnit] | None = _get_timeout(pyfuncitem)

        if timeout:
            testfunction = _wrap_with_timeout(testfunction, timeout)

        async def func() -> None:
            self._restore_logging_state()
            funcargs = pyfuncitem.funcargs

            kwargs: dict[str, Any] = {
                argname: resolve_fixture_arg(funcargs[argname])
                for argname in pyfuncitem._fixtureinfo.argnames
            }

            await testfunction(**kwargs)

        self._call = TestManager(
            func(),
            name=f"Test {pyfuncitem.name}",
            test_complete_cb=self._call_completed,
        )

        return True

    @hookimpl(trylast=True, wrapper=True)
    def pytest_runtest_makereport(
        self, item: Item, call: CallInfo[None]
    ) -> Generator[None, TestReport, TestReport]:
        """Create a :class:`~pytest.TestReport` for the setup, call, and teardown phases of a test item.

        The generated test report will contain additional properties about the simulation and cocotb:

        * ``cocotb``: Marks the report as a cocotb test report. Always set to ``True``.
        * ``sim_time_start``: The simulation time when the test phase started.
        * ``sim_time_stop``: The simulation time when the test phase ended.
        * ``sim_time_duration``: The simulation duration (stop - start) for the test phase.
        * ``sim_time_ratio``: The ratio of real time to simulation time.
        * ``sim_time_unit``: The time unit for the simulation. Possible values include: ``step``,
          ``fs``, ``ps``, ``ns``, ``us``, ``ms``, or ``sec``.
        * ``random_seed``: The seed value used for randomization.
        * ``file``: The file path of the test.
        * ``line``: The line number of the test.

        These properties are attached to the test report object and are included in outputs such as the
        JUnit XML report.

        Args:
            item: The pytest test Item.
            call: The :class:`~pytest.CallInfo` for the active test phase.

        Yields:
            None.

        Returns:
            The decorated :class:`~pytest.TestReport` containing simulation metadata.
        """
        report: TestReport = yield  # get generated test report from other plugins

        sim_time_stop: float = get_sim_time(self._sim_time_unit)
        sim_time_duration: float = sim_time_stop - self._sim_time_start
        sim_time_ratio: float = (
            (report.duration / sim_time_duration) if sim_time_duration else 0.0
        )

        # Additional properties that will be included with generated test report
        properties: dict[str, Any] = {
            "cocotb": True,
            "sim_time_start": self._sim_time_start,
            "sim_time_stop": sim_time_stop,
            "sim_time_duration": sim_time_duration,
            "sim_time_ratio": sim_time_ratio,
            "sim_time_unit": self._sim_time_unit,
            "random_seed": self._seed,
            "file": self._normalize_path(report.location[0]),
            "line": report.location[1],
        }

        # Make properties available for other plugins. The `extra` argument from pytest.TestReport
        # __init__(self, ..., **extra) constructor is doing the same
        report.__dict__.update(properties)

        # Make properties available in generated test reports like JUnit XML report
        report.user_properties.extend(properties.items())

        # Add file attachments to test report, this will be included in JUnit XML report
        for attachment in self._attachments:
            report.user_properties.append(("attachment", attachment))
            # pytest --override-ini=junit_logging=system-out|all ...
            report.sections.append(("Captured stdout", f"[[ATTACHMENT|{attachment}]]"))

        # If test failed, add COCOTB_RANDOM_SEED to captured stderr so that it will appear in JUnit XML
        # FIXME: the pytest internal junitxml plugin fails to report this correctly (gh-5226)
        if report.failed:
            # pytest --override-ini=junit_logging=system-err|all ...
            message: str = f"Test failed with COCOTB_RANDOM_SEED={cocotb.RANDOM_SEED}"
            report.sections.append(("Captured stderr", message))

        # Add file attachments for other plugins
        report.__dict__.update({"attachments": self._attachments})

        return report

    @hookimpl(tryfirst=True)
    def pytest_collectreport(self, report: CollectReport) -> None:
        """Handle a collection report by sending it to the parent process reporter."""
        self._send_report(report)

    @hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report: TestReport) -> None:
        """Handle a test report by sending it to the parent process reporter."""
        self._send_report(report)

    def _send_report(self, report: CollectReport | TestReport) -> None:
        """Serialize and send a report to the main test reporter via IPC."""
        if self._reporter_address:
            config: Config = self._session.config

            data: dict[str, Any] = config.hook.pytest_report_to_serializable(
                config=config, report=report
            )

            for retry in range(RETRIES, -1, -1):
                try:
                    with Client(self._reporter_address) as client:
                        client.send(data)
                    return
                except Exception:
                    if retry:
                        sleep(INTERVAL)
                    else:
                        self._notify_exception(ExceptionInfo.from_current())

    def _add_teardown(
        self,
        fixturedef: FixtureDef[Any],
        request: Any,
        iterator: AsyncGenerator[Any, None],
    ) -> None:
        """Register an asynchronous finalizer for a generator-based fixture.

        Args:
            fixturedef: The fixture definition.
            request: The fixture request.
            iterator: The asynchronous generator representing the fixture's execution.
        """

        async def func() -> None:
            self._restore_logging_state()

            try:
                await iterator.__anext__()
            except StopAsyncIteration:
                pass

        setup: TestManager = self._running_test
        teardown: TestManager = TestManager(
            func(),
            name=f"Teardown {request.fixturename}",
            test_complete_cb=self._teardown_completed,
        )

        def finalizer() -> None:
            # Assign setup tasks (without the main task) to test teardown
            if isinstance(setup, RunningTestSetup):
                for task in setup.subtasks:
                    if not task.cancelled():
                        teardown.add_task(task)

            self._teardowns.append(teardown)

        fixturedef.addfinalizer(finalizer)

    def _save_logging_state(self) -> None:
        """Save the current logging configuration state, including the root logger level."""
        self._logging_level = getLogger().level
        self._logging_restored = False

    def _restore_logging_state(self) -> None:
        """Restore log handlers required by pytest's output capture mechanism.

        These handlers are removed prematurely when the pytest logging plugin's
        context manager exits, which happens as soon as an async function is
        scheduled on the cocotb scheduler.
        """
        if not self._logging_restored and self._logging_plugin:
            root_logger: Logger = getLogger()
            root_logger.setLevel(self._logging_level)
            root_logger.addHandler(self._logging_plugin.log_file_handler)
            root_logger.addHandler(self._logging_plugin.log_cli_handler)
            root_logger.addHandler(self._logging_plugin.caplog_handler)
            root_logger.addHandler(self._logging_plugin.report_handler)
            self._logging_restored = True

    def _update_report_section(
        self, item: Item, when: Literal["setup", "call", "teardown"]
    ) -> None:
        """Capture logs for the active test phase and update the report section in the test item.

        Args:
            item: The pytest test Item.
            when: The active test phase.
        """
        if self._logging_plugin:
            log: str = self._logging_plugin.report_handler.stream.getvalue().strip()

            # Update the latest log section
            for index, section in reversed(list(enumerate(item._report_sections))):
                if section[0] == when and section[1] == "log":
                    item._report_sections[index] = (when, "log", log)
                    break

            # These log handlers are per test function phase, no needed anymore
            root_logger: Logger = getLogger()
            root_logger.setLevel(self._logging_root_level)
            root_logger.removeHandler(self._logging_plugin.caplog_handler)
            root_logger.removeHandler(self._logging_plugin.report_handler)

    def _on_sim_end(self) -> None:
        """Handle premature simulation termination by raising a SimFailure exception."""
        try:
            raise SimFailure(
                "cocotb expected it would shut down the simulation, but the simulation ended prematurely. "
                "This could be due to an assertion failure or a call to an exit routine in the HDL, "
                "or due to the simulator running out of events to process (is your clock running?)."
            )
        except BaseException:
            self._notify_exception(ExceptionInfo.from_current())
        finally:
            self._finish()

    def _start(self, running_test: TestManager) -> None:
        """Schedule and start a test phase (setup, call, or teardown).

        Args:
            running_test: The test manager instance representing the phase to execute.
        """
        self._running_test = running_test

        if self._scheduled:
            self._timer1._register(self._running_test.start)
        else:
            self._scheduled = True
            self._running_test.start()

    def _shutdown(self) -> None:
        """Shut down the cocotb environment and stop the simulator."""
        cocotb._shutdown._shutdown()

        # Setup simulator finalization
        cocotb.simulator.stop_simulator()

    def _normalize_path(self, path: Path | str) -> Path:
        """Resolve an absolute path to a relative path relative to ``_relative_to`` if possible."""

        if not isinstance(path, Path):
            path = Path(path)

        if path.is_absolute():
            try:
                return path.resolve().relative_to(self._relative_to)
            except ValueError:
                return path.resolve()

        return path

    def _normalize_paths(self, paths: Iterable[Path | str] | None) -> list[Path]:
        """Resolve a list of paths to be relative to ``_relative_to`` if possible."""
        return [self._normalize_path(path) for path in paths or () if path]


def _check_interactive_exception(call: CallInfo, report: TestReport) -> bool:
    """Check whether the exception raised during a call should trigger interactive debugging."""
    if call.excinfo is None:
        return False  # Didn't raise.

    if hasattr(report, "wasxfail"):
        return False  # Exception was expected.

    # Special control flow exception.
    return not isinstance(call.excinfo.value, (Skipped, bdb.BdbQuit))


def _interactive_exception(item: Item, call: CallInfo, report: TestReport) -> None:
    """Trigger the interactive debugger (pdb) hook for a test failure."""
    try:
        item.ihook.pytest_exception_interact(node=item, call=call, report=report)
    except Exit:
        pass


def _to_timeout(duration: float, unit: TimeUnit) -> tuple[float, TimeUnit]:
    """Convert duration and unit arguments to a timeout tuple."""
    return duration, unit


def _get_timeout(function: Function) -> tuple[float, TimeUnit] | None:
    """Retrieve the cocotb timeout marker settings from a test function, if present."""
    marker: Mark | None = function.get_closest_marker("cocotb_timeout")

    return _to_timeout(*marker.args, **marker.kwargs) if marker else None


def _wrap_with_timeout(
    func: Callable[..., Awaitable],
    timeout: tuple[float, TimeUnit],
) -> Callable[..., Awaitable]:
    """Wrap an asynchronous function with a timeout.

    Args:
        func: The asynchronous function to wrap.
        timeout: A tuple of (duration, unit) specifying the timeout.

    Returns:
        A wrapped asynchronous function that raises a timeout exception if it runs too long.
    """

    @wraps(func)
    async def wrapped(*args: object, **kwargs: object) -> Any:
        return await with_timeout(func(*args, **kwargs), timeout[0], timeout[1])

    return wrapped


def cocotb_top() -> SimHandleBase:
    """Return the handle to the top-level HDL entity/module (``cocotb.top``)."""
    return cocotb.top


_manager_inst: RegressionManager
"""The global regression manager instance."""
