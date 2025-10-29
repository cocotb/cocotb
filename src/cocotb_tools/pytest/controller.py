# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Internal cocotb plugin called ``cocotb_controller`` to run on top of cocotb runners.

This part of code is executed only from the main pytest parent process and not from
pytest sub-process (simulator).

Main responsibilities for this internal plugin are:

* Binding collected cocotb tests to cocotb runners
* Handling ``test_module`` and ``toplevel`` options from ``@pytest.mark.cocotb`` marker
* Handling test reports received from pytest sub-process (simulator) over IPC (Inter-Process Communication)
* Combining (mangling) identifiers from cocotb runner with cocotb test to generate new unique identifier
* Attaching additional properties about cocotb tests in JUnit XML tests report
"""

from __future__ import annotations

import inspect
import os
from collections.abc import Generator, Iterable
from multiprocessing.connection import Client, Listener
from pathlib import PurePosixPath
from threading import RLock, Thread
from typing import Any

from pytest import (
    Class,
    Collector,
    CollectReport,
    Config,
    ExceptionInfo,
    ExitCode,
    Function,
    Item,
    Module,
    Session,
    StashKey,
    TestReport,
    hookimpl,
)

import cocotb
from cocotb_tools.pytest.handle import MockSimHandle
from cocotb_tools.pytest.hdl import get_simulator
from cocotb_tools.pytest.runner import Runner


class Controller:
    """Internal cocotb plugin for pytest dedicated for the main pytest parent process."""

    def __init__(self, config: Config) -> None:
        """Create new instance of internal cocotb plugin for pytest.

        Args:
            config: Configuration object.
        """
        # Pytest configuration object
        self._config: Config = config

        # Instance of JUnit XML from built-in pytest junitxml plugin
        self._junitxml = None

        # Get handler to built-in pytest Junit XML plugin
        # This will be needed to add custom properties about cocotb tests and simulation
        junitxml = config.pluginmanager.getplugin("junitxml")

        if junitxml:
            # Instance of JUnit XML is stored in pytest stash where stash key to it
            # is stored in JUnix XML plugin
            key: StashKey | None = getattr(junitxml, "xml_key", None)
            self._junitxml = config.stash.get(key, None) if key else None

        self._listener: Listener | None = None
        self._thread: Thread | None = None
        self._lock = RLock()

        if "COCOTB_PYTEST_REPORTER_ADDRESS" not in os.environ:
            self._listener = Listener()
            self._thread = Thread(target=self._handle_test_reports)
            os.environ["COCOTB_PYTEST_REPORTER_ADDRESS"] = str(self._listener.address)

    @hookimpl(tryfirst=True)
    def pytest_configure(self, config: Config) -> None:
        """Configure environment for the main pytest parent process.

        Args:
            config: Pytest configuration object.
        """
        # Mock cocotb module for the main pytes parent process
        # Otherwise pytest can raise an exception when collecting test items
        #
        # Fun fact, this will not effect collection of test items done by pytest sub-process (simulator),
        # because collection of test items is done independently from it and with valid cocotb.top
        #
        # This may effect collected items when invoking pytest --collect-only
        # Some tests could be wrongly deselected when using boolean condition like this
        # @pytest.mark.skipif(cocotb.top.PARAMETER == 1) but this harmless
        #
        # TODO: Get version of HDL simulator, mostly: <command> --version
        # TODO: Get names and values of HDL parameters/generics, parse HDL source files?
        setattr(cocotb, "SIM_NAME", get_simulator(config))
        setattr(cocotb, "SIM_VERSION", "")
        setattr(cocotb, "top", MockSimHandle())

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_pycollect_makeitem(
        self, collector: Module | Class, name: str, obj: object
    ) -> Generator[Item | Collector | list[Item | Collector] | None, None, None]:
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

    @staticmethod
    def _split_nodeid(nodeid: str) -> tuple[PurePosixPath, str]:
        """Split provided node identifier to path and function name.

        Args:
            nodeid: Item nodeid in form of ``<path_to_file>::[<class_name>::]<function_name>``.

        Returns:
            Two-elements tuple with path to file and name of function with scope.
        """
        (path, _, function) = nodeid.partition("::")

        return PurePosixPath(path), function

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
        runner_path, runner_function = self._split_nodeid(runner_nodeid)
        item_path, item_function = self._split_nodeid(report.nodeid)

        if runner_path.parts == item_path.parts:
            return f"{runner_nodeid}::{item_function}"

        try:
            relative: PurePosixPath = item_path.relative_to(runner_path.parent)
            parts: tuple[str, ...] = relative.parent.parts
            packages: str = ".".join(parts) + "." if parts else ""

            return f"{runner_nodeid}::{packages}{relative.stem}::{item_function}"
        except ValueError:
            return f"{runner_nodeid}::{report.nodeid}"

    def _attach_properties_to_junit_xml(self, report: TestReport) -> None:
        # Pytest is always using "/" as path separator for nodes regadless of current OS environment
        address = report.nodeid.replace("/", ".").replace(".py::", ".")
        classname, _, name = address.rpartition("::")
        reporter = self._junitxml.node_reporter(report)

        reporter.add_attribute("classname", classname)
        reporter.add_attribute("name", name)

    @hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: Session) -> None:
        """Start thread to receive test reports from pytest sub-process (simulator)."""
        if self._thread:
            self._thread.start()

    @hookimpl(tryfirst=True)
    def pytest_sessionfinish(
        self, session: Session, exitstatus: int | ExitCode
    ) -> None:
        """Stop started thread."""
        if self._listener and self._thread:
            with Client(address=self._listener.address) as client:
                client.send(None)  # notify _run thread to exit

            self._thread.join()
            self._listener.close()

    def _collect(
        self, collector: Collector, items: Iterable[Item | Collector]
    ) -> Generator[Item | Collector, None, None]:
        """Collect and modify test items including cocotb runners and cocotb tests.

        Args:
            collector: Collector used to collect test items, mostly Python module.
            items: Collected test items by collector.

        Yields:
            Test items, including cocotb runners and cocotb tests.
        """
        collectonly: bool = collector.config.option.collectonly
        runner: Runner | None = collector.getparent(Runner)

        for item in items:
            if isinstance(item, Function) and item.get_closest_marker("cocotb"):
                if inspect.iscoroutinefunction(item.function):
                    if runner:
                        # Add cocotb runner keywords to cocotb test and vice versa
                        # This will allow to use pytest -k <expression> to select
                        # specific cocotb tests from specific cocotb runner and vice versa
                        item.extra_keyword_matches.update(runner.item.keywords)
                        runner.item.extra_keyword_matches.update(item.keywords)
                    elif collectonly:
                        # If test item is not under cocotb runner, show it during pytest --co
                        yield item
                elif not runner:
                    yield item

                    if item.parent:
                        yield Runner.from_parent(
                            item.parent,
                            name=item.name,
                            item=item,
                        )
            else:
                yield item

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

                        if self._junitxml:
                            self._attach_properties_to_junit_xml(report)

                        hook.pytest_runtest_logreport(report=report)

            except BaseException:
                self._notify_exception(ExceptionInfo.from_current())

    def _add_keywords(self, nodeid: str, keywords: Iterable[str]) -> None:
        """Store item keywords per node identifier.

        Args:
            nodeid: Node identifier of test item.
            keywords: List of test item keywords to stored under provided nodeid.
        """
        entries: set[str] | None = self._keywords.get(nodeid)

        if entries is None:
            self._keywords[nodeid] = set(keywords)
        else:
            entries.update(keywords)

    def _notify_exception(self, excinfo: ExceptionInfo) -> None:
        self._config.notify_exception(excinfo, self._config.option)
