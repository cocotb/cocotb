# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Pytest regression manager for cocotb."""

from __future__ import annotations

import bdb
import hashlib
import inspect
import random
from collections import deque
from collections.abc import AsyncGenerator, Awaitable, Generator, Iterable
from functools import wraps
from importlib import import_module
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
import cocotb._test
from cocotb import simulator
from cocotb._decorators import TestGenerator
from cocotb._extended_awaitables import with_timeout
from cocotb._gpi_triggers import Timer
from cocotb._test import RunningTest
from cocotb.simtime import TimeUnit, get_sim_time
from cocotb.task import Task
from cocotb_tools.pytest._compat import (
    is_cocotb_test,
    pre_process_collected_item,
)
from cocotb_tools.pytest._fixture import (
    AsyncFixture,
    AsyncFixtureCachedResult,
    resolve_fixture_arg,
)
from cocotb_tools.pytest._test import RunningTestSetup

RETRIES: int = 10
INTERVAL: float = 0.1  # seconds

AsyncFunction = Callable[..., Awaitable]
When = Literal["setup", "call", "teardown"]
"""Test phase."""


class SimFailure(BaseException):
    """A Test failure due to simulator failure. Used internally."""


def finish_on_exception(method: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap class method, capture exception, notify pytest and plugins, finish simulation."""

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
    """Pytest regression manager for cocotb."""

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
    ) -> None:
        """Create new instance of regression manager for cocotb tests.

        Args:
            args: Command line arguments for pytest.
            nodeid: Node identifier of cocotb runner.
            toplevel: Name of HDL top level design.
            xmlpath: Override the ``--junit-xml`` option.
            keywords: List of cocotb runner keywords.
            test_modules: List of test modules (Python modules with cocotb tests) to be loaded.
            invocation_dir: Path to directory location from where pytest was invoked.
            reporter_address: IPC address (Unix socket, Windows pipe, TCP, ...) to tests reporter.
            seed: Initialization value for the random number generator. If not provided, use current timestamp.
        """
        self._toplevel: str = toplevel
        """Name of top level."""

        self._running_test: RunningTest
        """Current running test: "setup", "call" or "teardown"."""

        self._setups: deque[RunningTest] = deque[RunningTest]()
        """List of test setups that were populated from the :py:func:`pytest.hookspec.pytest_fixture_setup` hook."""

        self._call: RunningTest | None = None
        """Test call that was populated from the :py:func:`pytest.hookspec.pytest_runtest_call` hook."""

        self._teardowns: deque[RunningTest] = deque[RunningTest]()
        """List of test teardowns that were populated from registered setup finalizers via
        :py:meth:`pytest.FixtureRequest.addfinalizer`` method.
        """

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

        # Unify it to current working directory where cocotb runner is running to avoid overriding it
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
        """Start regression manager."""
        self._session.config.hook.pytest_sessionstart(session=self._session)
        self._session.config.hook.pytest_collection(session=self._session)
        self._session.config.hook.pytest_runtestloop(session=self._session)

    @hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: Session) -> None:
        """Called after the :py:class:`pytest.Session` object has been created and
        before performing collection and entering the run test loop.

        Args:
            session: The pytest session object.
        """
        self._logging_plugin = session.config.pluginmanager.get_plugin("logging-plugin")

    @hookimpl(tryfirst=True)
    def pytest_report_header(self, config: Config, start_path: Path) -> str | list[str]:
        """Return a string or list of strings to be displayed as header info for terminal reporting.

        Args:
            config: The pytest config object.
            start_path: The starting dir.

        Returns:
            Lines returned by a plugin are displayed before those of plugins which ran before it.
        """
        return [
            f"Running on {cocotb.SIM_NAME} version {cocotb.SIM_VERSION}",
            f"Initialized cocotb v{cocotb.__version__} from {Path(__file__).parent.resolve()}",
            f"Seeding Python random module with {self._seed}",
            f"Top level set to {self._toplevel!r}",
        ]

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> Generator[
        None,
        Item | Collector | list[Item | Collector] | None,
        list[Item | Collector] | None,
    ]:
        # Convert @cocotb.* decorators to @pytest.mark.* markers
        pre_process_collected_item(obj)

        result: Item | Collector | list[Item | Collector] | None = yield

        if result is None:
            return None

        items: Iterable[Item | Collector] = (
            result if isinstance(result, list) else (result,)
        )

        return list(self._collect(items))

    @hookimpl(tryfirst=True)
    def pytest_runtestloop(self, session: Session) -> bool:
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
        """Perform the runtest protocol for a single test item.

        Args:
            item: Test item for which the runtest protocol is performed.
            nextitem: The scheduled-to-be-next test item (or ``None`` if this is the end my friend).
        """
        item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
        self._setup(item=item, nextitem=nextitem)

        return True

    @property
    def _item(self) -> Item:
        """Get current pytest item (test)."""
        return self._session.items[self._index]

    @property
    def _nextitem(self) -> Item | None:
        """Get next pytest item (test) needed by test teardown phase."""
        index: int = self._index + 1

        return self._session.items[index] if index < len(self._session.items) else None

    def _collect(
        self, items: Iterable[Item | Collector]
    ) -> Generator[Item | Collector, None, None]:
        for item in items:
            if not isinstance(item, Function):
                yield item

            elif is_cocotb_test(item):
                item.extra_keyword_matches.update(self._keywords)
                yield item

    def _call_and_report(
        self,
        item: Item,
        when: When,
        func: Callable[..., None] | None = None,
        **kwargs: object,
    ) -> TestReport:
        """Invoke test setup, call, teardown and generate test report from it.

        Args:
            item: The pytest item.
            when: Test setup, call or teardown.
            func: Test function that will be called.
            kwargs: Additional named arguments that will be passed to the test function.

        Returns:
            Test report.
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
        """Part of test setup, call or teardown completed callback.

        Args:
            item: The pytest item.
            when: Test "setup", "call" or "teardown".

        Returns:
            Test report.
        """
        self._update_report_section(item=item, when=when)

        return self._call_and_report(
            item=item, when=when, func=self._running_test.result().get
        )

    @finish_on_exception
    def _setup_completed(self) -> None:
        """Test setup completed callback."""
        item: Item = self._item
        nextitem: Item | None = self._nextitem

        report: TestReport = self._completed(item=item, when="setup")
        self._setup(item=item, nextitem=nextitem, report=report)

    def _setup(
        self, item: Item, nextitem: Item | None = None, report: TestReport | None = None
    ) -> None:
        """Test setup.

        Args:
            item: The pytest item.
            nextitem: The next pytest item. ``None`` if there are no more pytest items.
            report: Test report.
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
        """Test call completed callback."""
        item: Item = self._item
        nextitem: Item | None = self._nextitem

        report: TestReport = self._completed(item=item, when="call")
        item.ihook.pytest_runtest_logreport(report=report)
        self._teardown(item=item, nextitem=nextitem)

    @finish_on_exception
    def _teardown_completed(self) -> None:
        """Test teardown completed callback."""
        item: Item = self._item
        nextitem: Item | None = self._nextitem

        report: TestReport = self._completed(item=item, when="teardown")
        self._teardown(item=item, nextitem=nextitem, report=report)

    def _teardown(
        self, item: Item, nextitem: Item | None = None, report: TestReport | None = None
    ) -> None:
        """Test teardown.

        Args:
            item: The pytest item.
            nextitem: The next pytest item. ``None`` if there are no more pytest items.
            report: Test report.
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
        return self._item, self._nextitem

    def _pop_item(self) -> tuple[Item, Item | None]:
        self._index += 1

        return self._get_item()

    def _notify_exception(self, excinfo: ExceptionInfo) -> None:
        self._session.exitstatus = ExitCode.INTERNAL_ERROR
        self._session.config.notify_exception(excinfo, self._session.config.option)

    def _finish(self) -> None:
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
        """Called to perform the setup phase for a test item.

        Args:
            item: The pytest item (test function).
        """
        self._save_logging_state()

        # seed random number generator based on test module, name, and COCOTB_RANDOM_SEED
        hasher = hashlib.sha1()
        hasher.update(item.nodeid.encode())
        seed: int = self._seed + int(hasher.hexdigest(), 16)
        cocotb.RANDOM_SEED = seed
        self._random_state = random.getstate()
        random.seed(seed)

    @hookimpl(tryfirst=True)
    def pytest_runtest_call(self, item: Item) -> None:
        """Called to run the test for test item (the call phase).

        Args:
            item: The pytest item (test function).
        """
        self._save_logging_state()

    @hookimpl(tryfirst=True)
    def pytest_runtest_teardown(self, item: Item, nextitem: Item | None = None) -> None:
        """Called to perform the teardown phase for a test item.

        Args:
            item: The pytest item (test function).
            nextitem: The scheduled-to-be-next pytest item (next test function).
        """
        self._save_logging_state()

        # Restore random seed to original value
        cocotb.RANDOM_SEED = self._seed
        random.setstate(self._random_state)

    @hookimpl(tryfirst=True)
    def pytest_fixture_setup(
        self,
        fixturedef: FixtureDef[Any],
        request: Any,  # NOTE: type not available in public pytest API
    ) -> object | None:
        """Execution of fixture setup."""
        fixturefunc = fixturedef.func
        is_coroutine: bool = inspect.iscoroutinefunction(fixturefunc)
        is_async_generator: bool = inspect.isasyncgenfunction(fixturefunc)

        if not is_coroutine and not is_async_generator:
            return None

        func: Callable[[], Any]
        setup: RunningTest

        if is_async_generator:
            # Test setup with teardown, re-assign added sub-tasks during setup to teardown
            func = self._setup_async_generator(fixturedef, request)
        else:
            # Test setup-only without teardown
            func = self._setup_async_function(fixturedef, request)

        task: Task = AsyncFixture(func(), name=f"Setup {request.fixturename}")
        cache_key = fixturedef.cache_key(request)
        fixturedef.cached_result = AsyncFixtureCachedResult((task, cache_key, None))

        if is_async_generator:
            # Test setup with teardown, added sub-tasks during setup will be cancelled by test teardown
            setup = RunningTestSetup(self._setup_completed, task)
        else:
            # Test setup-only without teardown, run all tasks only during test setup
            setup = RunningTest(self._setup_completed, task)

        self._setups.append(setup)

        return True

    def _setup_async_generator(
        self,
        fixturedef: FixtureDef[Any],
        request: Any,
    ) -> Callable[[], Any]:
        """Test setup with teardown."""

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
        """Test setup-only without teardown."""

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
        testfunction = pyfuncitem.obj
        args: Iterable[object] = ()

        if isinstance(testfunction, TestGenerator):
            # Get test function from cocotb decorator object
            testfunction = testfunction.func

            if pyfuncitem.getparent(Class):
                # Pytest will create an instance for class but instance method is not correctly retrieved
                # by the pytest with getattr(instance, method_name) because it will get cocotb decorator object.
                # We must inject created instance (self) to method manually
                args = (pyfuncitem.instance,)  # self

        if not inspect.iscoroutinefunction(testfunction):
            return None

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

            await testfunction(*args, **kwargs)

        task: Task = Task(func(), name=f"Test {pyfuncitem.name}")
        self._call = RunningTest(self._call_completed, task)

        return True

    @hookimpl(trylast=True, wrapper=True)
    def pytest_runtest_makereport(
        self, item: Item, call: CallInfo[None]
    ) -> Generator[None, TestReport, TestReport]:
        """Called to create a :class:`~pytest.TestReport` for each of
        the setup, call and teardown runtest phases of a test item.

        Created test report will contain additional properties about simulation and cocotb:

        * `cocotb`: Mark test report as cocotb test report. Always set to True.
        * `sim_time_start`: Simulation time when specific test phase started.
        * `sim_time_stop`: Simulation time when specific test phase ended.
        * `sim_time_duration`: Simulation duration (stop - start) for specific test phase.
        * `sim_time_unit`: Time unit for simulation time. Possible values: `step`, `fs`, `ps`,
          `ns`, `us`, `ms` or `sec` (seconds).
        * `runner_nodeid`: Node identifier of cocotb runner (test to run simulator by pytest parent process).
        * `random_seed`: Value of seed used for randomization.

        Above properties are accessible from generated test report and they will be available from
        various generated test report outputs like JUnit XML report.

        Args:
            item: The item (test).
            call: The :class:`~pytest.CallInfo` for the test phase (setup, call, teardown).

        Returns:
            New object of test report with additional properties about simulation and cocotb.
        """
        report: TestReport = yield  # get generated test report from other plugins

        sim_time_stop: float = get_sim_time(self._sim_time_unit)

        # Additional properties that will be included with generated test report
        properties: dict[str, Any] = {
            "cocotb": True,
            "sim_time_start": self._sim_time_start,
            "sim_time_stop": sim_time_stop,
            "sim_time_duration": sim_time_stop - self._sim_time_start,
            "sim_time_unit": self._sim_time_unit,
            "runner_nodeid": self._nodeid,  # identify cocotb runner
            "random_seed": self._seed,
        }

        # Make properties available for other plugins. The `extra` argument from pytest.TestReport
        # __init__(self, ..., **extra) constructor is doing the same
        report.__dict__.update(properties)

        # Make properties available in generated test reports like JUnit XML report
        report.user_properties.extend(properties.items())

        return report

    @hookimpl(tryfirst=True)
    def pytest_runtest_logreport(self, report: TestReport) -> None:
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
        """Add asynchronous test teardown.

        Args:
            fixturedef: Definition of fixture.
            request: Fixture request.
            iterator: Asynchronous generator from invoked yield statement.
        """

        async def func() -> None:
            self._restore_logging_state()

            try:
                await iterator.__anext__()
            except StopAsyncIteration:
                pass

        task: Task = Task(func(), name=f"Teardown {request.fixturename}")
        setup: RunningTest = self._running_test
        teardown: RunningTest = RunningTest(self._teardown_completed, task)

        def finalizer() -> None:
            # Assign setup tasks (without the main task) to test teardown
            if isinstance(setup, RunningTestSetup):
                for task in setup.subtasks:
                    if not task.cancelled():
                        teardown.add_task(task)

            self._teardowns.append(teardown)

        fixturedef.addfinalizer(finalizer)

    def _save_logging_state(self) -> None:
        """Save state of logging including log handlers and current log level."""
        self._logging_level = getLogger().level
        self._logging_restored = False

    def _restore_logging_state(self) -> None:
        """Restore log handlers needed by pytest capture mechanism.

        These log handlers were unnecessary removed by using context manager in pytest logging plugin.
        Because how everything is working when using async functions, context manager exists immediately
        after scheduling async function to cocotb scheduler.
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
        """Update report section in item.

        Args:
            item: Test function.
            when: Test phase.
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

    def _start(self, running_test: RunningTest) -> None:
        """Start test setup, call or teardown.

        Args:
            running_test: Test to run.
        """
        self._running_test = running_test
        cocotb._test.set_current_test(running_test)

        if self._scheduled:
            self._timer1._register(self._running_test.start)
        else:
            self._scheduled = True
            self._running_test.start()

    def _shutdown(self) -> None:
        cocotb._shutdown._shutdown()

        # Setup simulator finalization
        simulator.stop_simulator()


def _check_interactive_exception(call: CallInfo, report: TestReport) -> bool:
    """Check whether the call raised an exception that should be reported as interactive."""
    if call.excinfo is None:
        return False  # Didn't raise.

    if hasattr(report, "wasxfail"):
        return False  # Exception was expected.

    # Special control flow exception.
    return not isinstance(call.excinfo.value, (Skipped, bdb.BdbQuit))


def _interactive_exception(item: Item, call: CallInfo, report: TestReport) -> None:
    """Interactive exception using Python Debugger (pdb)."""
    try:
        item.ihook.pytest_exception_interact(node=item, call=call, report=report)
    except Exit:
        pass


def _to_timeout(duration: float, unit: TimeUnit) -> tuple[float, TimeUnit]:
    """Helper function to extract ``*marker.args`` and ``**marker.kwargs`` to tuple."""
    return duration, unit


def _get_timeout(function: Function) -> tuple[float, TimeUnit] | None:
    """Get timeout from test function."""
    marker: Mark | None = function.get_closest_marker("cocotb_timeout")

    return _to_timeout(*marker.args, **marker.kwargs) if marker else None


def _wrap_with_timeout(
    func: Callable[..., Awaitable],
    timeout: tuple[float, TimeUnit],
) -> Callable[..., Awaitable]:
    """Wrap async test function (setup, call, teardown) with timeout."""

    @wraps(func)
    async def wrapped(*args: object, **kwargs: object) -> Any:
        return await with_timeout(func(*args, **kwargs), timeout[0], timeout[1])

    return wrapped
