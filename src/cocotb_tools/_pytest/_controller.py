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

import os
import shlex
from collections.abc import Generator, Iterable
from inspect import isasyncgenfunction, iscoroutinefunction
from multiprocessing.connection import Client, Listener
from pathlib import Path
from subprocess import run
from threading import RLock, Thread
from typing import Any
from warnings import warn

from _pytest.fixtures import FuncFixtureInfo
from _pytest.scope import Scope
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
    Package,
    Session,
    TestReport,
    hookimpl,
)

import cocotb
from cocotb_tools import _env
from cocotb_tools._pytest._handle import MockSimHandle
from cocotb_tools._pytest._junitxml import JUnitXML

#: Map scopes to scope classes
SCOPES: dict[str, type] = {
    "session": Session,
    "package": Package,
    "module": Module,
    "class": Class,
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


class Controller:
    """Internal cocotb plugin for pytest dedicated for the main pytest parent process."""

    def __init__(self, config: Config) -> None:
        """Create new instance of internal cocotb plugin for pytest.

        Args:
            config: Configuration object.
        """
        # Pytest configuration object
        self._config: Config = config

        # Collect-only
        self._collectonly: bool = config.option.collectonly

        # Detect if fixture was already seen (nodeid, fixture_name)
        self._seen: set[tuple[str, str]] = set()

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

        # All cocotb environment variables are captured as options by pytest plugin
        for name in _OPTION_ENVS:
            value: object = getattr(option, name, None)
            environment: str = name.upper()

            if value:
                os.environ[environment] = "1" if value is True else str(value)
            elif environment in os.environ:
                del os.environ[environment]

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
        Item | Collector | list[Item | Collector] | None,
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

        if self._collectonly:
            return result

        if result is None:
            return None

        items: Iterable[Item | Collector] = (
            result if isinstance(result, list) else (result,)
        )

        return list(filter(None, map(self._collect, items)))

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

    def _collect(self, item: Item | Collector) -> Item | Collector | None:
        """Collect test items including cocotb runners and cocotb tests.

        Args:
            collector: Collector used to collect test items, mostly Python module.
            items: Collected test items by collector.

        Yields:
            Test items, including cocotb runners and cocotb tests.
        """
        # Expect coroutine function with the @pytest.mark.cocotb marker
        if (
            not isinstance(item, Function)
            or not iscoroutinefunction(item.function)
            or item.get_closest_marker("cocotb") is None
        ):
            return item

        if not hasattr(item, "_fixtureinfo") or not item._fixtureinfo.argnames:
            warn(
                f"No fixtures provided for cocotb test. Ignoring test function {item.nodeid!r}"
            )
            return None

        info: FuncFixtureInfo = item._fixtureinfo

        # Name of DUT fixture
        fixture_name: str | None = None

        # Find fixture decorated with the @cocotb_tools.pytest.fixtures.dut decorator
        for argname in info.argnames:
            if argname in info.name2fixturedefs:
                # Fixtures can be stacked, last fixture is passed as argument to test function
                fixturedef: FixtureDef = info.name2fixturedefs[argname][-1]

                # This is set by the @cocotb_tools.pytest.fixtures.dut decorator
                if getattr(fixturedef.func, "__cocotb_dut_fixture__", False):
                    if fixture_name:
                        warn(
                            f"The {fixture_name!r} fixture will be used as DUT fixture. "
                            f"Ignoring redundant DUT fixture {argname!r} for {item.nodeid!r}"
                        )
                    else:
                        fixture_name = argname

        # Fixtures were decorated only with the @pytest.fixture, assume first argument as DUT fixture
        if fixture_name is None:
            fixture_name = info.argnames[0]

        # Fixtures can be stacked, last fixture is passed as argument to test function
        fixturedef = info.name2fixturedefs[fixture_name][-1]
        scope: str = fixturedef.scope
        name: str = fixture_name

        parent: Any = (
            item.parent if scope == "function" else item.getparent(SCOPES[scope])
        )

        # Fixture can be parametrized as well, generate name with [param...] brackets (pytest style)
        callspec = getattr(item, "callspec", None)
        params: list[str] = []

        if callspec:
            for arg, callscope in callspec._arg2scope.items():
                if callscope >= Scope(scope):
                    params.append(str(callspec.params[arg]))

        if params:
            name += "[" + "-".join(params) + "]"

        # DUT fixtures should be called once per scope
        # For example, DUT fixture with module scope should be used only once for that module
        seen: tuple[str, str] = (parent.nodeid, name)

        if seen in self._seen:
            return None

        self._seen.add(seen)
        argnames: tuple[str, ...] = (fixture_name,)

        item = Function.from_parent(
            parent=parent,
            name=name,
            originalname=fixture_name,
            callobj=run_simulation,
            callspec=callspec,
            fixtureinfo=FuncFixtureInfo(
                argnames=argnames,
                initialnames=argnames,
                names_closure=info.names_closure,
                name2fixturedefs=info.name2fixturedefs,
            ),
        )

        item.add_marker("cocotb")
        item.keywords["cocotb_runner"] = True

        return item

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
        is_coroutine: bool = iscoroutinefunction(fixturefunc)
        is_async_generator: bool = isasyncgenfunction(fixturefunc)
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
                        hook.pytest_runtest_logreport(report=report)

            except BaseException:
                self._notify_exception(ExceptionInfo.from_current())

    def _notify_exception(self, excinfo: ExceptionInfo) -> None:
        self._config.notify_exception(excinfo, self._config.option)


def run_simulation(**kwargs: Any) -> None:
    """Run simulation."""
    __tracebackhide__ = True

    # Pytest is passing values from fixtures as named arguments
    # Plugin ensures that created test function will have only one fixture
    name, sim = list(kwargs.items())[0]

    if callable(sim):
        sim()
    elif isinstance(sim, str):
        run(sim, check=True, shell=True)
    else:
        try:
            cmd = [str(arg) for arg in sim]
        except (TypeError, ValueError):
            raise TypeError(
                f"Unsupported result type {type(sim)!r} from DUT fixture {name!r}"
            ) from None
        else:
            run(cmd, check=True)
