# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Internal cocotb plugin to collect reports from the running HDL simulation process.

This code is executed solely within the main pytest parent process and not within
the simulation process. It establishes an IPC listener to collect test execution
results and logs sent back by the simulator.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from multiprocessing.connection import Client, Listener
from threading import RLock, Thread
from typing import Any

from pytest import (
    CollectReport,
    Config,
    ExceptionInfo,
    ExitCode,
    Session,
    TestReport,
    hookimpl,
)

from cocotb_tools import _env


class Reporter:
    """A reporter service that receives test results from the HDL simulation process.

    This class acts as a pytest plugin in the parent process. It listens on an IPC
    channel (e.g., a socket or pipe) for serialized test reports sent by the
    simulator-bound pytest subprocess and republishes them to pytest hooks.
    """

    def __init__(self, config: Config) -> None:
        """Initialize a new test reporter instance.

        Creates the IPC listener socket and initializes a background thread to receive and process incoming reports.

        Args:
            config: The pytest config object.
        """
        # Pytest configuration object
        self._config: Config = config

        # Pytest is printing test results in real-time when test finished execution
        # With default capturing mode (fd), it will print '.', 's', 'x', 'F', 'E' per test
        # The main pytest process will run test functions that will run HDL simulations
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
    def pytest_sessionstart(self, session: Session) -> None:
        """Start the background reporter thread when the pytest session starts.

        Args:
            session: The active pytest Session object.
        """
        if self._thread:
            self._thread.start()

    @hookimpl(tryfirst=True)
    def pytest_sessionfinish(
        self, session: Session, exitstatus: int | ExitCode
    ) -> None:
        """Stop the background reporter thread and close the listener.

        Args:
            session: The active pytest Session object.
            exitstatus: The exit status code of the session.
        """
        if self._thread:
            with Client(address=self._listener.address) as client:
                client.send(None)  # notify _run thread to exit

            self._thread.join()
            self._listener.close()

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_collectreport(
        self, report: CollectReport
    ) -> Generator[None, None, None]:
        """Wrap the collection report hook with a lock to ensure thread safety.

        Args:
            report: The pytest CollectReport to process.

        Yields:
            None.
        """
        with self._lock:
            yield

    @hookimpl(tryfirst=True, wrapper=True)
    def pytest_runtest_logreport(
        self, report: TestReport
    ) -> Generator[None, None, None]:
        """Wrap the test log report hook with a lock to ensure thread safety.

        Args:
            report: The pytest TestReport to process.

        Yields:
            None.
        """
        with self._lock:
            yield

    def _handle_test_reports(self) -> None:
        """Loop continuously to receive, deserialize, and forward reports from the simulator subprocess."""
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
                        hook.pytest_runtest_logreport(report=report)

                    elif isinstance(report, CollectReport):
                        hook.pytest_collectreport(report=report)

            except BaseException:
                self._config.notify_exception(
                    ExceptionInfo.from_current(), self._config.option
                )
