# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""All things relating to regression capabilities."""

from __future__ import annotations

import hashlib
import inspect
import logging
import os
import random
import re
import sys
import time
import warnings
from enum import Enum, auto
from importlib import import_module
from typing import Any, cast

import pytest

import cocotb
import cocotb._event_loop
import cocotb._shutdown as shutdown
import cocotb.types._resolve
from cocotb import logging as cocotb_logging
from cocotb import simulator
from cocotb._decorators import Test, TestGenerator
from cocotb._gpi_triggers import Timer
from cocotb._test_factory import TestFactory
from cocotb._test_manager import TestManager, TestSuccess
from cocotb._utils import DocEnum, safe_divide
from cocotb._xunit_reporter import XUnitReporter, bin_xml_escape
from cocotb.logging import ANSI
from cocotb.simtime import get_sim_time
from cocotb_tools import _env

__all__ = (
    "RegressionManager",
    "RegressionMode",
    "SimFailure",
    "Test",
    "TestFactory",
    "TestGenerator",
)

# Set __module__ on re-exports
TestGenerator.__module__ = __name__
Test.__module__ = __name__
TestFactory.__module__ = __name__


_TestFailures: tuple[type[BaseException], ...] = (
    AssertionError,
    pytest.raises.Exception,  # type: ignore[attr-defined]
)

if hasattr(pytest, "RaisesGroup") and hasattr(pytest, "RaisesExc"):

    def handle_pytest_exception_matchers(
        exc: BaseException,
        expected_error_set: set[
            type[BaseException] | pytest.RaisesExc | pytest.RaisesGroup
        ],
    ) -> tuple[set[pytest.RaisesExc | pytest.RaisesGroup], bool]:
        """Filter out :class:`pytest.RaisesExc` and :class:`pytest.RaisesGroup` exceptions and do checking on them.

        Args:
            exc: The exception result of the test.
            expected_error_set: The set of expected exceptions and :class:`!pytest.RaisesExc` and :class:`!pytest.RaisesGroup` objects.

        Returns:
            A tuple of the filtered out :class:`!pytest.RaisesExc` and :class:`!pytest.RaisesGroup` objects
            (so that the caller may remove them from the exception set)
            and a boolean whether there was a match.
        """
        exception_matcher_excs = cast(
            "set[pytest.RaisesExc | pytest.RaisesGroup]",
            {
                exc
                for exc in expected_error_set
                if isinstance(exc, (pytest.RaisesExc, pytest.RaisesGroup))
            },
        )

        for exception_matcher_exc in exception_matcher_excs:
            if exception_matcher_exc.matches(exc):
                # We got an exception that matches an exception matcher, so we consider the test passed.
                return exception_matcher_excs, True

        return exception_matcher_excs, False

else:

    def handle_pytest_exception_matchers(
        exc: BaseException,
        expected_error_set: set[
            type[BaseException] | pytest.RaisesExc | pytest.RaisesGroup
        ],
    ) -> tuple[set[pytest.RaisesExc | pytest.RaisesGroup], bool]:
        return set(), False


class SimFailure(BaseException):
    """A Test failure due to simulator failure.

    .. caution::
        Not to be raised or caught within a test.
        Only used for marking expected failure with ``expect_error`` in :func:`cocotb.test`.
    """


class RegressionTerminated(BaseException):
    """Indicates the regression was terminated early.

    The regression can be terminated early by setting :envvar:`COCOTB_MAX_FAILURES`.


    .. caution::
        Not intended to be raised or caught by user code.
        Used internally by the :class:`RegressionManager`.
    """


_logger = logging.getLogger(__name__)


def _format_doc(docstring: str | None) -> str:
    if docstring is None:
        return ""
    else:
        brief = docstring.split("\n")[0]
        return f"\n    {brief}"


class RegressionMode(DocEnum):
    """The mode of the :class:`RegressionManager`."""

    REGRESSION = (
        auto(),
        """Tests are run if included. Skipped tests are skipped, expected failures and errors are respected.""",
    )

    TESTCASE = (
        auto(),
        """Like :attr:`REGRESSION`, but skipped tests are *not* skipped if included.""",
    )


class _TestOutcome(Enum):
    PASS = auto()
    FAIL = auto()
    SKIP = auto()
    XFAIL = auto()


class _TestResults:
    def __init__(
        self,
        test_fullname: str,
        outcome: _TestOutcome,
        wall_time_s: float,
        sim_time_ns: float,
    ) -> None:
        self.test_fullname = test_fullname
        self.outcome = outcome
        self.wall_time_s = wall_time_s
        self.sim_time_ns = sim_time_ns

    @property
    def ratio(self) -> float:
        return safe_divide(self.sim_time_ns, self.wall_time_s)


class RegressionManager:
    """Object which manages tests.

    This object uses the builder pattern to build up a regression.
    Tests are added using :meth:`register_test` or :meth:`discover_tests`.
    Inclusion filters for tests can be added using :meth:`add_filters`.
    The "mode" of the regression can be controlled using :meth:`set_mode`.
    These methods can be called in any order any number of times before :meth:`start_regression` is called,
    and should not be called again after that.

    Once all the tests, filters, and regression behavior configuration is done,
    the user starts the regression with :meth:`start_regression`.
    This method must be called exactly once.

    Until the regression is started, :attr:`total_tests`, :attr:`count`, :attr:`passed`,
    :attr:`skipped`, and :attr:`failures` hold placeholder values.
    """

    COLOR_TEST = ANSI.BLUE_FG
    COLOR_PASSED = ANSI.GREEN_FG
    COLOR_SKIPPED = ANSI.YELLOW_FG
    COLOR_FAILED = ANSI.RED_FG
    COLOR_XFAILED = ANSI.YELLOW_FG

    _timer1 = Timer(1)

    def __init__(self) -> None:
        self._test: Test
        self._running_test: TestManager
        self.log = _logger
        self._regression_start_time: float
        self._test_results: list[_TestResults] = []
        self.total_tests = 0
        """Total number of tests that will be run or skipped."""
        self.count = 0
        """The current test count."""
        self.passed = 0
        """The current number of passed tests."""
        self.skipped = 0
        """The current number of skipped tests."""
        self.failures = 0
        """The current number of failed tests."""
        self._tearing_down = False
        self._test_queue: list[Test] = []
        self._filters: list[re.Pattern[str]] = []
        self._mode = RegressionMode.REGRESSION
        self._included: list[bool]
        self._regression_terminated: BaseException | None = None
        self._regression_seed = cocotb.RANDOM_SEED
        self._random_test_order = _env.as_bool(
            "COCOTB_RANDOM_TEST_ORDER", default=False
        )
        self._random_state: Any
        self._max_failures = _env.as_int("COCOTB_MAX_FAILURES", default=0)
        self._random_x_resolver_state: Any

        # Setup XUnit
        ###################

        results_filename = os.getenv("COCOTB_RESULTS_FILE", "results.xml")
        suite_name = os.getenv("COCOTB_RESULT_TESTSUITE", "all")
        package_name = os.getenv("COCOTB_RESULT_TESTPACKAGE", "all")

        self.xunit = XUnitReporter(filename=results_filename)
        self.xunit.add_testsuite(name=suite_name, package=package_name)
        self.xunit.add_property(name="random_seed", value=str(cocotb.RANDOM_SEED))

    def discover_tests(self, *modules: str) -> None:
        """Discover tests in files automatically.

        Should be called before :meth:`start_regression` is called.

        Args:
            modules: Each argument given is the name of a module where tests are found.
        """
        for module_name in modules:
            mod = import_module(module_name)

            found_test: bool = False
            for obj_name, obj in vars(mod).items():
                if isinstance(obj, Test):
                    found_test = True
                    self.register_test(obj)
                elif isinstance(obj, TestGenerator):
                    found_test = True
                    generated_tests: bool = False
                    for test in obj.generate_tests():
                        generated_tests = True
                        self.register_test(test)
                    if not generated_tests:
                        warnings.warn(
                            f"TestGenerator generated no tests: {module_name}.{obj_name}",
                            stacklevel=2,
                        )

            if not found_test:
                warnings.warn(
                    f"No tests were discovered in module: {module_name}", stacklevel=2
                )

        # error if no tests were discovered
        if not self._test_queue:
            modules_str = ", ".join(repr(m) for m in modules)
            raise RuntimeError(f"No tests were discovered in any module: {modules_str}")

    def add_filters(self, *filters: str) -> None:
        """Add regular expressions to filter-in registered tests.

        Only those tests which match at least one of the given filters are included;
        the rest are excluded.

        Should be called before :meth:`start_regression` is called.

        Args:
            filters: Each argument given is a regex pattern for test names.
                A match *includes* the test.
        """
        for filter in filters:
            compiled_filter = re.compile(filter)
            self._filters.append(compiled_filter)

    def set_mode(self, mode: RegressionMode) -> None:
        """Set the regression mode.

        See :class:`RegressionMode` for more details on how each mode affects :class:`RegressionManager` behavior.
        Should be called before :meth:`start_regression` is called.

        Args:
            mode: The regression mode to set.
        """
        self._mode = mode

    def register_test(self, test: Test) -> None:
        """Register a test with the :class:`RegressionManager`.

        Should be called before :meth:`start_regression` is called.

        Args:
            test: The test object to register.
        """
        self.log.debug("Registered test %r", test.fullname)
        self._test_queue.append(test)

    @classmethod
    def setup_pytest_assertion_rewriting(cls) -> None:
        """Configure pytest to rewrite assertions for better failure messages.

        Must be called before all modules containing tests are imported.
        """
        # Install the assertion rewriting hook, which must be done before we
        # import the test modules.
        from _pytest.assertion import install_importhook  # noqa: PLC0415
        from _pytest.config import Config  # noqa: PLC0415

        python_files = os.getenv("COCOTB_REWRITE_ASSERTION_FILES", "*.py").strip()
        if not python_files:
            # Even running the hook causes exceptions in some cases, so if the user
            # selects nothing, don't install the hook at all.
            return

        pytest_conf = Config.fromdictargs(
            {}, ["--capture=no", "-o", f"python_files={python_files}"]
        )
        install_importhook(pytest_conf)

    def start_regression(self) -> None:
        """Start the regression."""

        self.log.info("Running tests")

        # if needed, randomize tests before sorting into stages
        if self._random_test_order:
            random.shuffle(self._test_queue)

        # sort tests into stages
        self._test_queue.sort(key=lambda test: test.stage)

        # mark tests for running
        if self._filters:
            self._included = [False] * len(self._test_queue)
            for i, test in enumerate(self._test_queue):
                for filter in self._filters:
                    if filter.search(test.fullname):
                        self._included[i] = True
        else:
            self._included = [True] * len(self._test_queue)

        # compute counts
        self.count = 1
        self.total_tests = sum(self._included)
        if self.total_tests == 0:
            self.log.warning(
                "No tests left after filtering with: %s",
                ", ".join(f.pattern for f in self._filters),
            )

        # start test loop
        self._regression_start_time = time.time()
        self._first_test = True
        self._execute()

    def _execute(self) -> None:
        """Run the main regression loop.

        Used by :meth:`start_regression` and :meth:`_test_complete` to continue to the main test running loop,
        and by :meth:`_fail_regression` to shutdown the regression when a simulation failure occurs.
        """
        while self._test_queue:
            self._test = self._test_queue.pop(0)
            included = self._included.pop(0)

            # if the test is not included, record and continue
            if not included:
                self._record_test_excluded()
                continue

            # if the test is skipped, record and continue
            if self._test.skip and self._mode != RegressionMode.TESTCASE:
                self._record_test_skipped(wall_time_s=0, sim_time_ns=0, msg=None)
                continue

            # if the test should be run, but the simulator has failed, record and continue
            if self._regression_terminated is not None:
                self._score_test(
                    self._regression_terminated,
                    0,
                    0,
                )
                continue

            # initialize the test, if it fails, record and continue
            try:
                self._running_test = self._init_test()
            except Exception:
                self._record_test_init_failed()
                continue

            self._log_test_start()

            if self._first_test:
                self._first_test = False
                return self._schedule_next_test()
            else:
                self._timer1._register(self._schedule_next_test)
                return

        return self._tear_down()

    def _init_test(self) -> TestManager:
        coro = self._test.func(cocotb.top, *self._test.args, **self._test.kwargs)
        return TestManager(
            coro,
            test_complete_cb=self._test_complete,
            name=self._test.name,
            timeout=self._test.timeout,
        )

    def _schedule_next_test(self) -> None:
        # seed random number generator based on test module, name, and COCOTB_RANDOM_SEED
        hasher = hashlib.sha1()
        hasher.update(self._test.fullname.encode())
        test_seed = self._regression_seed + int(hasher.hexdigest(), 16)

        # seed random number generators with test seed
        self._random_state = random.getstate()
        random.seed(test_seed)
        self._random_x_resolver_state = (
            cocotb.types._resolve._randomResolveRng.getstate()
        )
        cocotb.types._resolve._randomResolveRng.seed(test_seed)
        cocotb.RANDOM_SEED = test_seed

        self._start_sim_time = get_sim_time("ns")
        self._start_time = time.time()

        self._running_test.start()

    def _tear_down(self) -> None:
        """Called by :meth:`_execute` when there are no more tests to run to finalize the regression."""
        # prevent re-entering the tear down procedure
        if not self._tearing_down:
            self._tearing_down = True
        else:
            return

        # Write out final log messages
        self._log_test_summary()

        # Generate output reports
        self.xunit.write()

        # We shut down here since the shutdown callback isn't called if stop_simulator is called.
        shutdown._shutdown()

        # Setup simulator finalization
        simulator.stop_simulator()

    def _test_complete(self) -> None:
        """Callback given to the test to be called when the test finished."""

        # compute wall time
        wall_time = time.time() - self._start_time
        sim_time_ns = get_sim_time("ns") - self._start_sim_time

        # restore random number generators state
        cocotb.RANDOM_SEED = self._regression_seed
        random.setstate(self._random_state)
        cocotb.types._resolve._randomResolveRng.setstate(self._random_x_resolver_state)

        exc: BaseException | None
        if self._regression_terminated is not None:
            # When the simulation is failing, we override the typical test results.
            exc = self._regression_terminated
        else:
            exc = self._running_test.exception()

        # Judge and record pass/fail.
        self._score_test(
            exc,
            wall_time,
            sim_time_ns,
        )

        # Run next test.
        return self._execute()

    def _score_test(
        self,
        exc: BaseException | None,
        wall_time_s: float,
        sim_time_ns: float,
    ) -> None:
        test = self._test

        if exc is not None:
            # These special exceptions take precedence over expect_error and expect_fail.
            if isinstance(exc, pytest.skip.Exception):
                # We got a skip exception, so we consider the test skipped.
                return self._record_test_skipped(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    msg=exc.msg,
                )
            elif isinstance(exc, pytest.xfail.Exception):
                # We got an xfail exception, so we consider the test xfailed.
                return self._record_test_xfail(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=None,
                    msg=exc.msg,
                )
            elif isinstance(exc, TestSuccess):
                return self._record_test_passed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                )
            if test.expect_error:
                expected_error_set = set(test.expect_error)

                # Filter out RaisesExc or RaisesGroup, which need to be handled differently.
                exception_matcher_excs, matched = handle_pytest_exception_matchers(
                    exc, expected_error_set
                )
                if matched:
                    # We got an RaisesExc or RaisesGroup that matches the expected exception.
                    return self._record_test_xfail(
                        wall_time_s=wall_time_s,
                        sim_time_ns=sim_time_ns,
                        result=exc,
                        msg="errored as expected",
                    )

                # Use isinstance with the remaining expected exceptions, which should all be exception types.
                expected_excs_set = cast(
                    "set[type[BaseException]]",
                    expected_error_set - exception_matcher_excs,
                )

                if isinstance(exc, tuple(expected_excs_set)):
                    # Non-exception group error with expected type.
                    return self._record_test_xfail(
                        wall_time_s=wall_time_s,
                        sim_time_ns=sim_time_ns,
                        result=exc,
                        msg="errored as expected",
                    )
                elif isinstance(exc, _TestFailures):
                    # We got a failure exception but expected an error.
                    return self._record_test_failed(
                        wall_time_s=wall_time_s,
                        sim_time_ns=sim_time_ns,
                        result=exc,
                        msg="failed but we expected an error",
                    )
                else:
                    # Non-exception group error with unexpected type.
                    return self._record_test_failed(
                        wall_time_s=wall_time_s,
                        sim_time_ns=sim_time_ns,
                        result=exc,
                        msg="errored with unexpected type",
                    )
            elif test.expect_fail:
                if isinstance(exc, _TestFailures):
                    # We expected a failure and got one.
                    return self._record_test_xfail(
                        wall_time_s=wall_time_s,
                        sim_time_ns=sim_time_ns,
                        result=exc,
                        msg="failed as expected",
                    )
                else:
                    # We expected a failure but got an unexpected exception type.
                    return self._record_test_failed(
                        wall_time_s=wall_time_s,
                        sim_time_ns=sim_time_ns,
                        result=exc,
                        msg="errored but we expected a failure",
                    )
            else:
                # We are not expecting an error or failure, but got an exception instead.
                return self._record_test_failed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=exc,
                    msg=None,
                )
        elif test.expect_error:
            # We expected an error but the test passed.
            return self._record_test_failed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=None,
                msg="passed but we expected an error",
            )
        elif test.expect_fail:
            # We expected a failure but the test passed.
            return self._record_test_failed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=None,
                msg="passed but we expected a failure",
            )
        else:
            # We expected a pass and got one.
            return self._record_test_passed(
                wall_time_s=wall_time_s, sim_time_ns=sim_time_ns
            )

    def _get_lineno(self, test: Test) -> int:
        try:
            return test.func.__code__.co_firstlineno
        except AttributeError:
            try:
                return inspect.getsourcelines(test.func)[1]
            except OSError:
                return 1

    def _log_test_start(self) -> None:
        """Called by :meth:`_execute` to log that a test is starting."""
        hilight_start = "" if cocotb_logging.strip_ansi else self.COLOR_TEST
        hilight_end = "" if cocotb_logging.strip_ansi else ANSI.DEFAULT
        self.log.info(
            "%srunning%s %s (%d/%d)%s",
            hilight_start,
            hilight_end,
            self._test.fullname,
            self.count,
            self.total_tests,
            _format_doc(self._test.doc),
        )

    def _record_test_excluded(self) -> None:
        """Called by :meth:`_execute` when a test is excluded by filters."""

        # write out xunit results
        lineno = self._get_lineno(self._test)
        self.xunit.add_testcase(
            name=self._test.name,
            classname=self._test.module,
            file=inspect.getfile(self._test.func),
            lineno=repr(lineno),
            time=repr(0),
            sim_time_ns=repr(0),
            ratio_time=repr(0),
        )
        self.xunit.add_skipped()

        # do not log anything, nor save details for the summary

    def _record_test_skipped(
        self,
        wall_time_s: float,
        sim_time_ns: float,
        msg: str | None,
    ) -> None:
        """Called by :meth:`_execute` when a test is skipped."""

        # log test results
        hilight_start = "" if cocotb_logging.strip_ansi else self.COLOR_SKIPPED
        hilight_end = "" if cocotb_logging.strip_ansi else ANSI.DEFAULT
        if msg is not None:
            msg = f": {msg}"
        else:
            msg = f" ({self.count}/{self.total_tests}){_format_doc(self._test.doc)}"
        self.log.info(
            "%sskipping%s %s%s",
            hilight_start,
            hilight_end,
            self._test.fullname,
            msg,
        )

        # write out xunit results
        lineno = self._get_lineno(self._test)
        self.xunit.add_testcase(
            name=self._test.name,
            classname=self._test.module,
            file=inspect.getfile(self._test.func),
            lineno=repr(lineno),
            time=repr(0),
            sim_time_ns=repr(0),
            ratio_time=repr(0),
        )
        self.xunit.add_skipped()

        # save details for summary
        self._test_results.append(
            _TestResults(
                test_fullname=self._test.fullname,
                outcome=_TestOutcome.SKIP,
                sim_time_ns=sim_time_ns,
                wall_time_s=wall_time_s,
            )
        )

        # update running passed/failed/skipped counts
        self.skipped += 1
        self.count += 1

    def _record_test_init_failed(self) -> None:
        """Called by :meth:`_execute` when a test initialization fails."""

        # log test results
        hilight_start = "" if cocotb_logging.strip_ansi else self.COLOR_FAILED
        hilight_end = "" if cocotb_logging.strip_ansi else ANSI.DEFAULT
        self.log.exception(
            "%sFailed to initialize%s %s! (%d/%d)%s",
            hilight_start,
            hilight_end,
            self._test.fullname,
            self.count,
            self.total_tests,
            _format_doc(self._test.doc),
        )

        # write out xunit results
        lineno = self._get_lineno(self._test)
        self.xunit.add_testcase(
            name=self._test.name,
            classname=self._test.module,
            file=inspect.getfile(self._test.func),
            lineno=repr(lineno),
            time=repr(0),
            sim_time_ns=repr(0),
            ratio_time=repr(0),
        )
        self.xunit.add_failure(msg="Test initialization failed")

        # save details for summary
        self._test_results.append(
            _TestResults(
                test_fullname=self._test.fullname,
                outcome=_TestOutcome.FAIL,
                sim_time_ns=0,
                wall_time_s=0,
            )
        )

        # update running passed/failed/skipped counts
        self.failures += 1
        self.count += 1

    def _record_test_xfail(
        self,
        wall_time_s: float,
        sim_time_ns: float,
        result: BaseException | None,
        msg: str | None,
    ) -> None:
        start_hilight = "" if cocotb_logging.strip_ansi else self.COLOR_PASSED
        stop_hilight = "" if cocotb_logging.strip_ansi else ANSI.DEFAULT
        if msg is None:
            rest = ""
        else:
            rest = f": {msg}"
        if result is None:
            result_was = ""
        else:
            result_was = f" (result was {type(result).__qualname__})"
        self.log.info(
            "%s %spassed%s%s%s",
            self._test.fullname,
            start_hilight,
            stop_hilight,
            rest,
            result_was,
            exc_info=result,
        )

        # write out xunit results
        ratio_time = safe_divide(sim_time_ns, wall_time_s)
        lineno = self._get_lineno(self._test)
        self.xunit.add_testcase(
            name=self._test.name,
            classname=self._test.module,
            file=inspect.getfile(self._test.func),
            lineno=repr(lineno),
            time=repr(wall_time_s),
            sim_time_ns=repr(sim_time_ns),
            ratio_time=repr(ratio_time),
        )

        # update running passed/failed/skipped counts
        self.passed += 1
        self.count += 1

        # save details for summary
        self._test_results.append(
            _TestResults(
                test_fullname=self._test.fullname,
                outcome=_TestOutcome.PASS,
                sim_time_ns=sim_time_ns,
                wall_time_s=wall_time_s,
            )
        )

    def _record_test_passed(
        self,
        wall_time_s: float,
        sim_time_ns: float,
    ) -> None:
        start_hilight = "" if cocotb_logging.strip_ansi else self.COLOR_PASSED
        stop_hilight = "" if cocotb_logging.strip_ansi else ANSI.DEFAULT
        self.log.info(
            "%s %spassed%s",
            self._test.fullname,
            start_hilight,
            stop_hilight,
        )

        # write out xunit results
        ratio_time = safe_divide(sim_time_ns, wall_time_s)
        lineno = self._get_lineno(self._test)
        self.xunit.add_testcase(
            name=self._test.name,
            classname=self._test.module,
            file=inspect.getfile(self._test.func),
            lineno=repr(lineno),
            time=repr(wall_time_s),
            sim_time_ns=repr(sim_time_ns),
            ratio_time=repr(ratio_time),
        )

        # update running passed/failed/skipped counts
        self.passed += 1
        self.count += 1

        # save details for summary
        self._test_results.append(
            _TestResults(
                test_fullname=self._test.fullname,
                outcome=_TestOutcome.PASS,
                sim_time_ns=sim_time_ns,
                wall_time_s=wall_time_s,
            )
        )

    def _record_test_failed(
        self,
        wall_time_s: float,
        sim_time_ns: float,
        result: BaseException | None,
        msg: str | None,
    ) -> None:
        start_hilight = "" if cocotb_logging.strip_ansi else self.COLOR_FAILED
        stop_hilight = "" if cocotb_logging.strip_ansi else ANSI.DEFAULT
        if msg is None:
            rest = ""
        else:
            rest = f": {msg}"
        self.log.warning(
            "%s%s %sfailed%s%s",
            stop_hilight,
            self._test.fullname,
            start_hilight,
            stop_hilight,
            rest,
            exc_info=result,
        )

        # write out xunit results
        ratio_time = safe_divide(sim_time_ns, wall_time_s)
        lineno = self._get_lineno(self._test)
        self.xunit.add_testcase(
            name=self._test.name,
            classname=self._test.module,
            file=inspect.getfile(self._test.func),
            lineno=repr(lineno),
            time=repr(wall_time_s),
            sim_time_ns=repr(sim_time_ns),
            ratio_time=repr(ratio_time),
        )
        self.xunit.add_failure(
            error_type=type(result).__name__, error_msg=bin_xml_escape(result)
        )

        # update running passed/failed/skipped counts
        self.failures += 1
        self.count += 1

        # save details for summary
        self._test_results.append(
            _TestResults(
                test_fullname=self._test.fullname,
                outcome=_TestOutcome.FAIL,
                sim_time_ns=sim_time_ns,
                wall_time_s=wall_time_s,
            )
        )
        if (
            self._regression_terminated is None
            and self._max_failures > 0
            and self.failures >= self._max_failures
        ):
            self._regression_terminated = RegressionTerminated(
                f"Regression stopped after {self.failures} failures "
                f"(limit={self._max_failures})"
            )
            self.log.warning(self._regression_terminated)

    def _log_test_summary(self) -> None:
        """Called by :meth:`_tear_down` to log the test summary."""
        real_time = time.time() - self._regression_start_time
        sim_time_ns = get_sim_time("ns")
        ratio_time = safe_divide(sim_time_ns, real_time)

        if len(self._test_results) == 0:
            return

        TEST_FIELD = "TEST"
        RESULT_FIELD = "STATUS"
        SIM_FIELD = "SIM TIME (ns)"
        REAL_FIELD = "REAL TIME (s)"
        RATIO_FIELD = "RATIO (ns/s)"
        TOTAL_NAME = f"TESTS={self.total_tests} PASS={self.passed} FAIL={self.failures} SKIP={self.skipped}"

        TEST_FIELD_LEN = max(
            len(TEST_FIELD),
            len(TOTAL_NAME),
            len(max([x.test_fullname for x in self._test_results], key=len)),
        )
        RESULT_FIELD_LEN = len(RESULT_FIELD)
        SIM_FIELD_LEN = len(SIM_FIELD)
        REAL_FIELD_LEN = len(REAL_FIELD)
        RATIO_FIELD_LEN = len(RATIO_FIELD)

        header_dict = {
            "a": TEST_FIELD,
            "b": RESULT_FIELD,
            "c": SIM_FIELD,
            "d": REAL_FIELD,
            "e": RATIO_FIELD,
            "a_len": TEST_FIELD_LEN,
            "b_len": RESULT_FIELD_LEN,
            "c_len": SIM_FIELD_LEN,
            "d_len": REAL_FIELD_LEN,
            "e_len": RATIO_FIELD_LEN,
        }

        LINE_LEN = (
            3
            + TEST_FIELD_LEN
            + 2
            + RESULT_FIELD_LEN
            + 2
            + SIM_FIELD_LEN
            + 2
            + REAL_FIELD_LEN
            + 2
            + RATIO_FIELD_LEN
            + 3
        )

        LINE_SEP = "*" * LINE_LEN + "\n"

        summary = ""
        summary += LINE_SEP
        summary += "** {a:<{a_len}}  {b:^{b_len}}  {c:>{c_len}}  {d:>{d_len}}  {e:>{e_len}} **\n".format(
            **header_dict
        )
        summary += LINE_SEP

        test_line = "** {a:<{a_len}}  {start}{b:^{b_len}}{end}  {c:>{c_len}.2f}   {d:>{d_len}.2f}   {e:>{e_len}}  **\n"
        hilite: str
        lolite: str
        for result in self._test_results:
            if result.outcome == _TestOutcome.SKIP:
                ratio = "-.--"
                pass_fail_str = "SKIP"
                hilite = self.COLOR_SKIPPED
                lolite = ANSI.DEFAULT
            elif result.outcome == _TestOutcome.PASS:
                ratio = format(result.ratio, "0.2f")
                pass_fail_str = "PASS"
                hilite = self.COLOR_PASSED
                lolite = ANSI.DEFAULT
            elif result.outcome == _TestOutcome.FAIL:
                ratio = format(result.ratio, "0.2f")
                pass_fail_str = "FAIL"
                hilite = self.COLOR_FAILED
                lolite = ANSI.DEFAULT
            elif result.outcome == _TestOutcome.XFAIL:
                ratio = format(result.ratio, "0.2f")
                pass_fail_str = "XFAIL"
                hilite = self.COLOR_XFAILED
                lolite = ANSI.DEFAULT

            if cocotb_logging.strip_ansi:
                hilite = ""
                lolite = ""

            test_dict = {
                "a": result.test_fullname,
                "b": pass_fail_str,
                "c": result.sim_time_ns,
                "d": result.wall_time_s,
                "e": ratio,
                "a_len": TEST_FIELD_LEN,
                "b_len": RESULT_FIELD_LEN,
                "c_len": SIM_FIELD_LEN - 1,
                "d_len": REAL_FIELD_LEN - 1,
                "e_len": RATIO_FIELD_LEN - 1,
                "start": hilite,
                "end": lolite,
            }

            summary += test_line.format(**test_dict)

        summary += LINE_SEP

        summary += test_line.format(
            a=TOTAL_NAME,
            b="",
            c=sim_time_ns,
            d=real_time,
            e=format(ratio_time, "0.2f"),
            a_len=TEST_FIELD_LEN,
            b_len=RESULT_FIELD_LEN,
            c_len=SIM_FIELD_LEN - 1,
            d_len=REAL_FIELD_LEN - 1,
            e_len=RATIO_FIELD_LEN - 1,
            start="",
            end="",
        )

        summary += LINE_SEP

        self.log.info(summary)

    def _on_sim_end(self) -> None:
        """Called when the simulator shuts down."""

        # We are already shutting down, this is expected.
        if self._tearing_down:
            return

        msg = (
            "cocotb expected it would shut down the simulation, but the simulation ended prematurely. "
            "This could be due to an assertion failure or a call to an exit routine in the HDL, "
            "or due to the simulator running out of events to process (is your clock running?)."
        )

        # We assume if we get here, the simulation ended unexpectedly due to an assertion failure,
        # or due to an end of events from the simulator.
        self._regression_terminated = SimFailure(msg)
        self._running_test.cancel(msg)
        cocotb._event_loop._inst.run()

    def list_tests(self) -> None:
        """List the tests that would be run, without running them."""
        self.log.info(
            "Listing tests that were discovered, in the order they would be run."
        )
        for test in self._test_queue:
            print(test.fullname)
        self.log.info("All tests listed. Exiting.")


_manager_inst: RegressionManager
"""The global regression manager instance."""


def _setup_regression_manager() -> None:
    """Setup the global regression manager instance."""
    global _manager_inst
    _manager_inst = RegressionManager()

    # discover tests
    modules: list[str] = _env.as_list("COCOTB_TEST_MODULES")
    if not modules:
        raise RuntimeError(
            "Environment variable COCOTB_TEST_MODULES, which defines the module(s) to execute, is not defined or empty."
        )
    _manager_inst.setup_pytest_assertion_rewriting()
    _manager_inst.discover_tests(*modules)

    # filter tests
    testcases: list[str] = _env.as_list("COCOTB_TESTCASE")
    test_filter: str = _env.as_str("COCOTB_TEST_FILTER")
    if testcases and test_filter:
        raise RuntimeError("Specify only one of COCOTB_TESTCASE or COCOTB_TEST_FILTER")
    elif testcases:
        warnings.warn(
            "COCOTB_TESTCASE is deprecated in favor of COCOTB_TEST_FILTER",
            DeprecationWarning,
            stacklevel=2,
        )
        filters: list[str] = [f"{testcase}$" for testcase in testcases]
        _manager_inst.add_filters(*filters)
        _manager_inst.set_mode(RegressionMode.TESTCASE)
    elif test_filter:
        _manager_inst.add_filters(test_filter)
        _manager_inst.set_mode(RegressionMode.TESTCASE)


def _run_regression() -> None:
    """Setup and run a regression."""

    # sys.path normally includes "" (the current directory), but does not appear to when Python is embedded.
    # Add it back because users expect to be able to import files in their test directory.
    sys.path.insert(0, "")

    # From https://www.python.org/dev/peps/pep-0565/#recommended-filter-settings-for-test-runners
    # If the user doesn't want to see these, they can always change the global
    # warning settings in their test module.
    if not sys.warnoptions:
        warnings.simplefilter("default")

    _setup_regression_manager()

    if _env.as_bool("COCOTB_LIST_TESTS", False):
        _manager_inst.list_tests()
    else:
        _manager_inst.start_regression()
        shutdown.register(_manager_inst._on_sim_end)
