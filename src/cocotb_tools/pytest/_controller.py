# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Internal cocotb plugin called ``cocotb_controller`` to run on top of cocotb runners.

This part of code is executed only from the main pytest parent process and not from
pytest sub-process (simulator).

Main responsibilities for this internal plugin are:

* Binding collected cocotb tests to cocotb runners
* Handling test reports received from pytest sub-process (simulator) over IPC (Inter-Process Communication)
* Combining (mangling) identifiers from cocotb runner with cocotb test to generate new unique identifier
* Attaching additional properties about cocotb tests in JUnit XML tests report
"""

from __future__ import annotations

import inspect
import os
import shlex
from collections.abc import Generator, Iterable
from multiprocessing.connection import Client, Listener
from pathlib import Path
from threading import RLock, Thread
from typing import Any

from pytest import (
    Class,
    Collector,
    CollectReport,
    Config,
    ExceptionInfo,
    ExitCode,
    FixtureDef,
    Function,
    Item,
    Module,
    Session,
    TestReport,
    hookimpl,
)

import cocotb
from cocotb_tools import _env
from cocotb_tools.pytest._handle import MockSimHandle
from cocotb_tools.pytest._junitxml import JUnitXML
from cocotb_tools.pytest._runner import Runner


class Controller:
    """Internal cocotb plugin for pytest dedicated for the main pytest parent process."""

    def __init__(self, config: Config) -> None:
        """Create new instance of internal cocotb plugin for pytest.

        Args:
            config: Configuration object.
        """
        # Pytest configuration object
        self._config: Config = config

        # Pytest is printing test results in real-time when test finished execution
        # With default capturing mode (fd), it will print '.', 's', 'x', 'F', 'E' per test
        # The main pytest process will run test functions that will run HDL simulations (aka runners)
        # Each HDL simulation will take some time and it will execute N cocotb tests
        # To print test results in real-time from running cocotb tests,
        # we need a separate single thread that will run in parallel to running HDL simulation and
        # receive test reports from it
        # On top of that, xdist will schedule HDL simulations in separate processes
        # producing cocotb test reports in parallel and independently to each other
        self._listener: Listener
        self._thread: Thread | None = None

        # RLock (Reentrant Lock) is needed to protect resources in other plugins
        # when the running thread will invoke the pytest_runtest_logreport hook to
        # notify other plugins about new cocotb test result received from HDL simulator
        # Pytest hooks can be wrapped and called recursively
        self._lock = RLock()

        # Create only a single reporter service in the main parent process
        # In case when plugin is used with xdist, it must be created within xdist dsession to
        # receive test results from xdist workers
        if not _env.exists("COCOTB_PYTEST_REPORTER_ADDRESS"):
            self._listener = Listener()
            self._thread = Thread(target=self._handle_test_reports)
            os.environ["COCOTB_PYTEST_REPORTER_ADDRESS"] = str(self._listener.address)

    @hookimpl(tryfirst=True)
    def pytest_configure(self, config: Config) -> None:
        """Configure environment for the main pytest parent process.

        Args:
            config: Pytest configuration object.
        """
        option = config.option

        invocation_dir: Path | str = (
            option.cocotb_pytest_dir or config.invocation_params.dir or Path.cwd()
        )

        invocation_args: Iterable[str] = (
            option.cocotb_pytest_args or config.invocation_params.args or ()
        )

        # Populate environment variables for cocotb runners that will run HDL simulators
        os.environ["PYGPI_USERS"] = ",".join(option.pygpi_users)
        os.environ["COCOTB_RANDOM_SEED"] = str(option.cocotb_seed)
        os.environ["COCOTB_PYTEST_DIR"] = str(Path(invocation_dir).resolve())
        os.environ["COCOTB_PYTEST_ARGS"] = shlex.join(invocation_args)

        if option.cocotb_waveform_viewer:
            os.environ["COCOTB_WAVEFORM_VIEWER"] = option.cocotb_waveform_viewer

        if option.cocotb_attach:
            os.environ["COCOTB_ATTACH"] = str(option.cocotb_attach)

        if option.cocotb_resolve_x:
            os.environ["COCOTB_RESOLVE_X"] = option.cocotb_resolve_x

        if option.cocotb_scheduler_debug:
            os.environ["COCOTB_SCHEDULER_DEBUG"] = "1"

        if option.cocotb_trust_inertial_writes:
            os.environ["COCOTB_TRUST_INERTIAL_WRITES"] = "1"

        # Mock cocotb module for the main pytest parent process
        # Otherwise pytest can raise an exception when loading Python module
        #
        # When invoking pytest with --collect-only option, markers like
        # @pytest.mark.skip() or @pytest.mark.skipif() are ignored anyway because
        # test will be skipped during runtime (pytest without --collect-only).
        #
        # There is no need for the main pytest process to collect tests from HDL simulators.
        # Cocotb tests will be properly collected and executed with valid cocotb.top simulation handle by
        # pytest instance that is running from HDL simulator and report back to the main pytest process.
        setattr(cocotb, "SIM_NAME", option.cocotb_simulator)
        setattr(cocotb, "SIM_VERSION", "")
        setattr(cocotb, "top", MockSimHandle())

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> Generator[
        None,
        Item | Collector | list[Item | Collector] | None,
        list[Item | Collector] | None,
    ]:
        """Collect cocotb runners and cocotb tests from Python modules.

        Args:
            collector: Python module or class containing cocotb runners or cocotb tests.
            name: Name of collected item (test function, cocotb runner, cocotb test).
            obj: Object representation of collected item (test function, cocotb runner, cocotb test).

        Yields:
            Collected test function, cocotb runner or cocotb test.
        """
        result: Item | Collector | list[Item | Collector] | None = yield

        if result is None:
            return None

        items: Iterable[Item | Collector] = (
            result if isinstance(result, list) else (result,)
        )

        return list(self._collect(collector, items))

    @hookimpl(tryfirst=True)
    def pytest_runtest_setup(self, item: Item) -> None:
        """Setup environment for pytest sub-process (simulator)
        that will be started as test function from the main pytest parent process.

        Args:
            item: Test function.
        """
        # Expose cocotb runner nodeid and keywords from the main pytest parent process
        # to pytest sub-process (simulator) via environment variables
        os.environ["COCOTB_PYTEST_NODEID"] = item.nodeid
        os.environ["COCOTB_PYTEST_KEYWORDS"] = ",".join(item.keywords)

    def _get_mangled_nodeid(self, report: TestReport) -> str:
        """Get mangled address of test node identifier as combination of node identifiers from cocotb runner and test.

        Pytest is always using ``/`` as path separator (compatible with POSIX).
        Node identifier is mostly represented as: ``<path_to_file>::[<class_name>::]<function_name>``

        To get unique test identifier for cocotb test from various different cocotb runners,
        we need to combine node identifier from cocotb runner and cocotb test.

        Args:
            report: Test report from simulator (pytest sub-process).

        Returns:
            Mangled node identifier.
        """
        runner_nodeid: str = getattr(report, "runner_nodeid", "")
        runner_path, _, runner_function = runner_nodeid.partition("::")
        item_path, _, item_function = report.nodeid.partition("::")

        if runner_path == item_path:
            # We don't need to include path from item because it is already present in runner
            return f"{runner_nodeid}::{item_function}"

        # Pytest is always using / as separator regadless of OS environment
        runner_dir: str = runner_path.rpartition("/")[0]
        item_dir: str = item_path.rpartition("/")[0]

        if item_dir.startswith(runner_dir):
            test_module: str = (
                item_path.removeprefix(runner_dir)
                .removesuffix(".py")
                .strip("/")
                .replace("/", ".")
            )

            return f"{runner_nodeid}::{test_module}::{item_function}"

        return f"{runner_nodeid}::{report.nodeid}"

    @hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: Session) -> None:
        """Start thread to receive test reports from pytest sub-process (simulator)."""
        JUnitXML.register(session.config)

        if self._thread:
            self._thread.start()

    @hookimpl(tryfirst=True)
    def pytest_sessionfinish(
        self, session: Session, exitstatus: int | ExitCode
    ) -> None:
        """Stop started thread."""
        if self._thread:
            with Client(address=self._listener.address) as client:
                client.send(None)  # notify _run thread to exit

            self._thread.join()
            self._listener.close()

    def _collect(
        self, collector: Collector, items: Iterable[Item | Collector]
    ) -> Generator[Item | Collector, None, None]:
        """Collect test items including cocotb runners and cocotb tests.

        It will help to build hierarchy tree of cocotb runners and cocotb tests.

        When invoking ``pytest`` with ``--collect-only`` option::

            <Dir tests>
                <Module test_sample_module.py>
                    <Runner test_sample_module>
                        <Testbench test_sample_module>
                            <Function test_feature>

        When invoking ``pytest`` without ``--collect-only`` option::

            <Dir tests>
                <Module test_sample_module.py>
                    <Function test_sample_module>

        Tree created with ``--collect-only`` option is to help users to visualize
        hierarchy tree of cocotb runners and cocotb tests.

        Args:
            collector: Collector used to collect test items, mostly Python module.
            items: Collected test items by collector.

        Yields:
            Test items, including cocotb runners and cocotb tests.
        """
        collectonly: bool = collector.config.option.collectonly
        runner: Runner | None = collector.getparent(Runner)

        for item in items:
            if not isinstance(item, Function):
                yield item

            elif inspect.iscoroutinefunction(item.function):
                if item.get_closest_marker("cocotb_runner"):
                    item.warn(
                        UserWarning(
                            "You have applied @pytest.mark.cocotb_runner marker on coroutine function. "
                            f"This is an usage mistake. Please remove it from {item.nodeid!r}"
                        )
                    )
                elif item.get_closest_marker("cocotb_test"):
                    if runner:
                        # Collected cocotb test must be always under cocotb runner
                        if collectonly:
                            # Show collected cocotb test under cocotb runner when invoking pytest --collect-only
                            # It will help user to visualize hierarchy tree of cocotb tests and cocotb runners
                            yield item
                        else:
                            # Add cocotb test keywords to cocotb runner
                            # This will allow to run cocotb runner by using keywords associated with cocotb test
                            runner.item.extra_keyword_matches.update(item.keywords)
                            # Skip cocotb test here, it will be collected by pytest that is running from HDL simulator
                else:
                    yield item  # some coroutine test function that is not part of cocotb

            elif item.get_closest_marker("cocotb_test"):
                item.warn(
                    UserWarning(
                        "You have applied @pytest.mark.cocotb_test marker on non-async test function. "
                        f"This is an usage mistake. Please remove it from {item.nodeid!r}"
                    )
                )
            elif item.get_closest_marker("cocotb_runner"):
                # Avoid recursion of cocotb runners
                if not runner:
                    if not collectonly:
                        # Don't show collected cocotb runner as <Function> because it will be duplicated with <Runner>
                        # <Module file>
                        #   <Function name>       <--- cocotb runner as test function (it will be not showed)
                        #   <Runner name>         <--- cocotb runner as collector of cocotb tests
                        #     <Testbench name>    <--- test module aka testbench (Python module with cocotb tests)
                        #       <Function name>   <--- cocotb test
                        yield item

                    if item.parent:
                        yield Runner.from_parent(
                            item.parent,
                            name=item.name,
                            item=item,
                        )
            else:
                yield item  # some test function that is not part of cocotb

    def pytest_fixture_setup(
        self, fixturedef: FixtureDef, request: Any
    ) -> object | None:
        """Skip applying async fixture to non-async test functions when fixture autouse was used.

        Args:
            fixturedef: The fixture definition object.
            request: The fixture request object.

        Returns:
            True when async fixture will be skipped. Otherwise None and continue with next plugin.
        """
        fixturefunc = fixturedef.func
        is_coroutine: bool = inspect.iscoroutinefunction(fixturefunc)
        is_async_generator: bool = inspect.isasyncgenfunction(fixturefunc)
        autouse: bool = getattr(fixturedef, "_autouse", False)

        if autouse and (is_coroutine or is_async_generator):
            cache_key = fixturedef.cache_key(request)
            fixturedef.cached_result = (None, cache_key, None)
            return True

        return None

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_runtest_logreport(
        self, report: TestReport
    ) -> Generator[None, None, None]:
        with self._lock:
            yield

    def _handle_test_reports(self) -> None:
        """Main thread for receiving cocotb test reports from pytest sub-process (simulator)."""
        config: Config = self._config
        hook = config.hook

        while True:
            try:
                with self._listener.accept() as connection:
                    data: dict[str, Any] | None = connection.recv()

                    if data is None:
                        return  # terminate thread

                    report: CollectReport | TestReport | None = (
                        hook.pytest_report_from_serializable(config=config, data=data)
                    )

                    if isinstance(report, TestReport):
                        report.nodeid = self._get_mangled_nodeid(report)
                        hook.pytest_runtest_logreport(report=report)

            except BaseException:
                self._notify_exception(ExceptionInfo.from_current())

    def _notify_exception(self, excinfo: ExceptionInfo) -> None:
        self._config.notify_exception(excinfo, self._config.option)
