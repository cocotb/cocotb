# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""All things relating to regression capabilities."""

import functools
import hashlib
import inspect
import logging
import os
import random
import re
import time
import warnings
from enum import auto
from importlib import import_module
from typing import (
    Callable,
    Coroutine,
    List,
    Union,
)

import cocotb
import cocotb._gpi_triggers
import cocotb.handle
from cocotb import _ANSI, simulator
from cocotb._base_triggers import Trigger
from cocotb._decorators import Parameterized, Test
from cocotb._extended_awaitables import SimTimeoutError, with_timeout
from cocotb._gpi_triggers import GPITrigger, Timer
from cocotb._outcomes import Error, Outcome
from cocotb._test import RunningTest
from cocotb._test_factory import TestFactory
from cocotb._test_functions import Failed
from cocotb._utils import (
    DocEnum,
    remove_traceback_frames,
    safe_divide,
    want_color_output,
)
from cocotb._xunit_reporter import XUnitReporter
from cocotb.task import Task
from cocotb.utils import get_sim_time

__all__ = (
    "Parameterized",
    "RegressionManager",
    "RegressionMode",
    "SimFailure",
    "Test",
    "TestFactory",
)

# Set __module__ on re-exports
Parameterized.__module__ = __name__
Test.__module__ = __name__
TestFactory.__module__ = __name__


class SimFailure(BaseException):
    """A Test failure due to simulator failure."""


_logger = logging.getLogger(__name__)


def _format_doc(docstring: Union[str, None]) -> str:
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


class _TestResults:
    # TODO Replace with dataclass in Python 3.7+

    def __init__(
        self,
        test_fullname: str,
        passed: Union[None, bool],
        wall_time_s: float,
        sim_time_ns: float,
    ) -> None:
        self.test_fullname = test_fullname
        self.passed = passed
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

    _timer1 = Timer(1)

    def __init__(self) -> None:
        self._test: Test
        self._running_test: RunningTest
        self.log = _logger
        self._regression_start_time: float
        self._test_results: List[_TestResults] = []
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
        self._test_queue: List[Test] = []
        self._filters: List[re.Pattern[str]] = []
        self._mode = RegressionMode.REGRESSION
        self._included: List[bool]
        self._sim_failure: Union[Error[None], None] = None

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
                elif isinstance(obj, Parameterized):
                    found_test = True
                    generated_tests: bool = False
                    for test in obj.generate_tests():
                        generated_tests = True
                        self.register_test(test)
                    if not generated_tests:
                        warnings.warn(
                            f"Parametrize object generated no tests: {module_name}.{obj_name}",
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
        try:
            import pytest  # noqa: PLC0415
        except ImportError:
            _logger.info(
                "pytest not found, install it to enable better AssertionError messages"
            )
            return
        try:
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
        except Exception:
            _logger.exception(
                "Configuring the assertion rewrite hook using pytest %s failed. "
                "Please file a bug report!",
                pytest.__version__,
            )

    def start_regression(self) -> None:
        """Start the regression."""

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

        # start write scheduler
        cocotb.handle._start_write_scheduler()

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
                self._record_test_skipped()
                continue

            # if the test should be run, but the simulator has failed, record and continue
            if self._sim_failure is not None:
                self._score_test(
                    self._sim_failure,
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
                return self._timer1._prime(self._schedule_next_test)

        return self._tear_down()

    def _init_test(self) -> RunningTest:
        # wrap test function in timeout
        func: Callable[..., Coroutine[Trigger, None, None]]
        timeout = self._test.timeout_time
        if timeout is not None:
            f = self._test.func

            @functools.wraps(f)
            async def func(*args: object, **kwargs: object) -> None:
                running_co = Task(f(*args, **kwargs))

                try:
                    await with_timeout(running_co, timeout, self._test.timeout_unit)
                except SimTimeoutError:
                    running_co.cancel()
                    raise
        else:
            func = self._test.func

        main_task = Task(func(cocotb.top), name=f"Test {self._test.name}")
        return RunningTest(self._test_complete, main_task)

    def _schedule_next_test(self, trigger: Union[GPITrigger, None] = None) -> None:
        if trigger is not None:
            # TODO move to Trigger object
            cocotb._gpi_triggers._current_gpi_trigger = trigger
            trigger._cleanup()

        # seed random number generator based on test module, name, and COCOTB_RANDOM_SEED
        hasher = hashlib.sha1()
        hasher.update(self._test.fullname.encode())
        seed = cocotb.RANDOM_SEED + int(hasher.hexdigest(), 16)
        random.seed(seed)

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

        assert not self._test_queue

        # stop the write scheduler
        cocotb.handle._stop_write_scheduler()

        # Write out final log messages
        self._log_test_summary()

        # Generate output reports
        self.xunit.write()

        # TODO refactor initialization and finalization into their own module
        # to prevent circular imports requiring local imports
        from cocotb._init import _shutdown_testbench  # noqa: PLC0415

        _shutdown_testbench()

        # Setup simulator finalization
        simulator.stop_simulator()

    def _test_complete(self) -> None:
        """Callback given to the test to be called when the test finished."""

        # compute wall time
        wall_time = time.time() - self._start_time
        sim_time_ns = get_sim_time("ns") - self._start_sim_time

        # Judge and record pass/fail.
        self._score_test(
            self._running_test.result(),
            wall_time,
            sim_time_ns,
        )

        # Run next test.
        return self._execute()

    def _score_test(
        self,
        outcome: Outcome[None],
        wall_time_s: float,
        sim_time_ns: float,
    ) -> None:
        test = self._test

        # score test
        passed: bool
        msg: Union[str, None]
        exc: Union[BaseException, None]
        try:
            outcome.get()
        except BaseException as e:
            passed, msg = False, None
            exc = remove_traceback_frames(e, ["_score_test", "get"])
        else:
            passed, msg, exc = True, None, None

        if passed:
            if test.expect_error:
                self._record_test_failed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=exc,
                    msg="passed but we expected an error",
                )
                passed = False

            elif test.expect_fail:
                self._record_test_failed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=exc,
                    msg="passed but we expected a failure",
                )
                passed = False

            else:
                self._record_test_passed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=None,
                    msg=msg,
                )

        elif test.expect_fail:
            if isinstance(exc, (AssertionError, Failed)):
                self._record_test_passed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=None,
                    msg="failed as expected",
                )

            else:
                self._record_test_failed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=exc,
                    msg="expected failure, but errored with unexpected type",
                )
                passed = False

        elif test.expect_error:
            if isinstance(exc, test.expect_error):
                self._record_test_passed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=None,
                    msg="errored as expected",
                )

            else:
                self._record_test_failed(
                    wall_time_s=wall_time_s,
                    sim_time_ns=sim_time_ns,
                    result=exc,
                    msg="errored with unexpected type",
                )
                passed = False

        else:
            self._record_test_failed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=exc,
                msg=msg,
            )

    def _get_lineno(self, test: Test) -> int:
        try:
            return inspect.getsourcelines(test.func)[1]
        except OSError:
            return 1

    def _log_test_start(self) -> None:
        """Called by :meth:`_execute` to log that a test is starting."""
        hilight_start = _ANSI.COLOR_TEST if want_color_output() else ""
        hilight_end = _ANSI.COLOR_DEFAULT if want_color_output() else ""
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

    def _record_test_skipped(self) -> None:
        """Called by :meth:`_execute` when a test is skipped."""

        # log test results
        hilight_start = _ANSI.COLOR_SKIPPED if want_color_output() else ""
        hilight_end = _ANSI.COLOR_DEFAULT if want_color_output() else ""
        self.log.info(
            "%sskipping%s %s (%d/%d)%s",
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
        self.xunit.add_skipped()

        # save details for summary
        self._test_results.append(
            _TestResults(
                test_fullname=self._test.fullname,
                passed=None,
                sim_time_ns=0,
                wall_time_s=0,
            )
        )

        # update running passed/failed/skipped counts
        self.skipped += 1
        self.count += 1

    def _record_test_init_failed(self) -> None:
        """Called by :meth:`_execute` when a test initialization fails."""

        # log test results
        hilight_start = _ANSI.COLOR_FAILED if want_color_output() else ""
        hilight_end = _ANSI.COLOR_DEFAULT if want_color_output() else ""
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
                passed=False,
                sim_time_ns=0,
                wall_time_s=0,
            )
        )

        # update running passed/failed/skipped counts
        self.failures += 1
        self.count += 1

    def _record_test_passed(
        self,
        wall_time_s: float,
        sim_time_ns: float,
        result: Union[Exception, None],
        msg: Union[str, None],
    ) -> None:
        start_hilight = _ANSI.COLOR_PASSED if want_color_output() else ""
        stop_hilight = _ANSI.COLOR_DEFAULT if want_color_output() else ""
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
                passed=True,
                sim_time_ns=sim_time_ns,
                wall_time_s=wall_time_s,
            )
        )

    def _record_test_failed(
        self,
        wall_time_s: float,
        sim_time_ns: float,
        result: Union[BaseException, None],
        msg: Union[str, None],
    ) -> None:
        start_hilight = _ANSI.COLOR_FAILED if want_color_output() else ""
        stop_hilight = _ANSI.COLOR_DEFAULT if want_color_output() else ""
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
        self.xunit.add_failure(error_type=type(result).__name__, error_msg=str(result))

        # update running passed/failed/skipped counts
        self.failures += 1
        self.count += 1

        # save details for summary
        self._test_results.append(
            _TestResults(
                test_fullname=self._test.fullname,
                passed=False,
                sim_time_ns=sim_time_ns,
                wall_time_s=wall_time_s,
            )
        )

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
        for result in self._test_results:
            hilite = ""
            lolite = ""

            if result.passed is None:
                ratio = "-.--"
                pass_fail_str = "SKIP"
                if want_color_output():
                    hilite = _ANSI.COLOR_SKIPPED
                    lolite = _ANSI.COLOR_DEFAULT
            elif result.passed:
                ratio = format(result.ratio, "0.2f")
                pass_fail_str = "PASS"
                if want_color_output():
                    hilite = _ANSI.COLOR_PASSED
                    lolite = _ANSI.COLOR_DEFAULT
            else:
                ratio = format(result.ratio, "0.2f")
                pass_fail_str = "FAIL"
                if want_color_output():
                    hilite = _ANSI.COLOR_FAILED
                    lolite = _ANSI.COLOR_DEFAULT

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

    def _fail_simulation(self, msg: str) -> None:
        self._sim_failure = Error(SimFailure(msg))
        self._running_test.abort(self._sim_failure)
        cocotb._scheduler_inst._event_loop()
