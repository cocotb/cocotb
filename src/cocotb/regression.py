# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""All things relating to regression capabilities."""

import functools
import hashlib
import inspect
import logging
import os
import pdb
import random
import re
import time
import warnings
from enum import auto
from importlib import import_module
from itertools import product
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import cocotb
import cocotb._profiling
import cocotb._scheduler
import cocotb._write_scheduler
from cocotb import _ANSI, simulator
from cocotb._utils import (
    DocEnum,
    remove_traceback_frames,
    want_color_output,
)
from cocotb._xunit_reporter import XUnitReporter
from cocotb.result import TestSuccess
from cocotb.sim_time_utils import get_sim_time
from cocotb.task import Task, _RunningTest
from cocotb.triggers import SimTimeoutError, Timer, Trigger

_pdb_on_exception = "COCOTB_PDB_ON_EXCEPTION" in os.environ


_logger = logging.getLogger(__name__)

_Failed: Type[BaseException]
try:
    import pytest
except ModuleNotFoundError:
    _Failed = AssertionError
else:
    try:
        with pytest.raises(Exception):
            pass
    except BaseException as _raises_e:
        _Failed = type(_raises_e)
    else:
        assert False, "pytest.raises doesn't raise an exception when it fails"


# TODO remove SimFailure once we have functionality in place to abort the test without
# having to set an exception.
class SimFailure(Exception):
    """A Test failure due to simulator failure."""


class Test:
    """A cocotb test in a regression.

    Args:
        func:
            The test function object.

        name:
            The name of the test function.
            Defaults to ``func.__qualname__`` (the dotted path to the test function in the module).

        module:
            The name of the module containing the test function.
            Defaults to ``func.__module__`` (the name of the module containing the test function).

        doc:
            The docstring for the test.
            Defaults to ``func.__doc__`` (the docstring of the test function).

        timeout_time:
            Simulation time duration before the test is forced to fail with a :exc:`~cocotb.triggers.SimTimeoutError`.

        timeout_unit:
            Units of ``timeout_time``, accepts any units that :class:`~cocotb.triggers.Timer` does.

        expect_fail:
            If ``True`` and the test fails a functional check via an ``assert`` statement, :pytest:class:`pytest.raises`,
            :pytest:class:`pytest.warns`, or :pytest:class:`pytest.deprecated_call`, the test is considered to have passed.
            If ``True`` and the test passes successfully, the test is considered to have failed.

        expect_error:
            Mark the result as a pass only if one of the given exception types is raised in the test.

        skip:
            Don't execute this test as part of the regression.
            The test can still be run manually by setting :envvar:`COCOTB_TESTCASE`.

        stage:
            Order tests logically into stages.
            Tests from earlier stages are run before tests from later stages.
    """

    def __init__(
        self,
        *,
        func: Callable[..., Coroutine[Any, Any, None]],
        name: Optional[str] = None,
        module: Optional[str] = None,
        doc: Optional[str] = None,
        timeout_time: Optional[float] = None,
        timeout_unit: str = "step",
        expect_fail: bool = False,
        expect_error: Union[Type[Exception], Sequence[Type[Exception]]] = (),
        skip: bool = False,
        stage: int = 0,
        _expect_sim_failure: bool = False,
    ) -> None:
        if timeout_time is not None:
            co = func  # must save ref because we overwrite variable "func"

            @functools.wraps(func)
            async def func(*args, **kwargs):
                running_co = Task(co(*args, **kwargs))

                try:
                    res = await cocotb.triggers.with_timeout(
                        running_co, self.timeout_time, self.timeout_unit
                    )
                except SimTimeoutError:
                    running_co.kill()
                    raise
                else:
                    return res

        self.func = func
        self.timeout_time = timeout_time
        self.timeout_unit = timeout_unit
        self.expect_fail = expect_fail
        if isinstance(expect_error, BaseException):
            expect_error = (expect_error,)
        if _expect_sim_failure:
            expect_error += (SimFailure,)
        self.expect_error = expect_error
        self._expect_sim_failure = _expect_sim_failure
        self.skip = skip
        self.stage = stage
        self.name = self.func.__qualname__ if name is None else name
        self.module = self.func.__module__ if module is None else module
        self.doc = self.func.__doc__ if doc is None else doc
        if self.doc is not None:
            # cleanup docstring using `trim` function from PEP257
            self.doc = inspect.cleandoc(self.doc)
        self.fullname = f"{self.module}.{self.name}"


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
        self._test_task: Task[None]
        self._test_start_time: float
        self._test_start_sim_time: float
        self.log = _logger
        self._regression_start_time: float
        self._test_results: List[Dict[str, Any]] = []
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
        self._sim_failure: Union[SimFailure, None] = None

        # Setup XUnit
        ###################

        results_filename = os.getenv("COCOTB_RESULTS_FILE", "results.xml")
        suite_name = os.getenv("COCOTB_RESULT_TESTSUITE", "all")
        package_name = os.getenv("COCOTB_RESULT_TESTPACKAGE", "all")

        self.xunit = XUnitReporter(filename=results_filename)
        self.xunit.add_testsuite(name=suite_name, package=package_name)
        self.xunit.add_property(name="random_seed", value=str(cocotb._random_seed))

    def discover_tests(self, *modules: str) -> None:
        """Discover tests in files automatically.

        Should be called before :meth:`start_regression` is called.

        Args:
            modules: Each argument given is the name of a module where tests are found.

        Raises:
            RuntimeError: If no tests are found in any of the provided modules.
        """
        for module_name in modules:
            mod = import_module(module_name)

            if not hasattr(mod, "__cocotb_tests__"):
                raise RuntimeError(
                    f"No tests were discovered in module: {module_name!r}"
                )

            for test in mod.__cocotb_tests__:
                self.register_test(test)

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
            import pytest
        except ImportError:
            _logger.info(
                "pytest not found, install it to enable better AssertionError messages"
            )
            return
        try:
            # Install the assertion rewriting hook, which must be done before we
            # import the test modules.
            from _pytest.assertion import install_importhook
            from _pytest.config import Config

            pytest_conf = Config.fromdictargs(
                {}, ["--capture=no", "-o", "python_files=*.py"]
            )
            install_importhook(pytest_conf)
        except Exception:
            _logger.exception(
                f"Configuring the assertion rewrite hook using pytest {pytest.__version__} failed. "
                "Please file a bug report!"
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
                self._record_sim_failure()
                continue

            # initialize the test, if it fails, record and continue
            try:
                self._test_task = _RunningTest(
                    self._test.func(cocotb.top), self._test.name
                )
            except Exception:
                self._record_test_init_failed()
                continue

            self._log_test_start()

            # seed random number generator based on test module, name, and COCOTB_RANDOM_SEED
            hasher = hashlib.sha1()
            hasher.update(self._test.fullname.encode())
            seed = cocotb._random_seed + int(hasher.hexdigest(), 16)
            random.seed(seed)

            self._test_start_sim_time = get_sim_time("ns")
            self._test_start_time = time.time()

            if self._first_test:
                self._first_test = False
                return self._schedule_next_test()
            else:
                return self._timer1._prime(self._schedule_next_test)

        return self._tear_down()

    def _schedule_next_test(self, trigger: Optional[Trigger] = None) -> None:
        if trigger is not None:
            # TODO move to Trigger object
            cocotb.sim_phase = cocotb.SimPhase.NORMAL
            trigger._unprime()
        cocotb._write_scheduler.start_write_scheduler()
        cocotb._scheduler_inst._add_test(self._test_task)

    def _tear_down(self) -> None:
        """Called by :meth:`_execute` when there are no more tests to run to finalize the regression."""
        # prevent re-entering the tear down procedure
        if not self._tearing_down:
            self._tearing_down = True
        else:
            return

        assert not self._test_queue

        # Write out final log messages
        self._log_test_summary()

        # Generate output reports
        self.xunit.write()

        # Setup simulator finalization
        simulator.stop_simulator()
        cocotb._profiling.finalize()
        cocotb._stop_user_coverage()
        cocotb._stop_library_coverage()

    def _test_complete(self) -> None:
        """Callback given to the scheduler, to be called when the current test completes.

        Due to the way that simulation failure is handled,
        this function must be able to detect simulation failure and finalize the regression.
        """

        # compute test completion time
        wall_time_s = time.time() - self._test_start_time
        sim_time_ns = get_sim_time("ns") - self._test_start_sim_time
        test = self._test

        # clean up write scheduler
        cocotb._write_scheduler.stop_write_scheduler()

        # score test
        try:
            self._test_task._outcome.get()
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as e:
            result = remove_traceback_frames(e, ["_test_complete", "get"])
        else:
            result = TestSuccess()

        if (
            isinstance(result, TestSuccess)
            and not test.expect_fail
            and not test.expect_error
        ):
            self._record_test_passed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=None,
                msg=None,
            )

        elif isinstance(result, TestSuccess) and test.expect_error:
            self._record_test_failed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=None,
                msg="passed but we expected an error",
            )

        elif isinstance(result, TestSuccess):
            self._record_test_failed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=None,
                msg="passed but we expected a failure",
            )

        elif isinstance(result, (AssertionError, _Failed)) and test.expect_fail:
            self._record_test_passed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=None,
                msg="failed as expected",
            )

        elif test.expect_error:
            if isinstance(result, test.expect_error):
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
                    result=result,
                    msg="errored with unexpected type",
                )

        else:
            self._record_test_failed(
                wall_time_s=wall_time_s,
                sim_time_ns=sim_time_ns,
                result=result,
                msg=None,
            )

            if _pdb_on_exception:
                pdb.post_mortem(result.__traceback__)

        # continue test loop, assuming sim failure or not
        return self._execute()

    def _get_lineno(self, test: Test) -> None:
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
            {
                "test": self._test.fullname,
                "pass": None,
                "sim": 0,
                "real": 0,
            }
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
            {
                "test": self._test.fullname,
                "pass": False,
                "sim": 0,
                "real": 0,
            }
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
        ratio_time = self._safe_divide(sim_time_ns, wall_time_s)
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
            {
                "test": self._test.fullname,
                "pass": True,
                "sim": sim_time_ns,
                "real": wall_time_s,
                "ratio": ratio_time,
            }
        )

    def _record_test_failed(
        self,
        wall_time_s: float,
        sim_time_ns: float,
        result: Union[Exception, None],
        msg: Union[str, None],
    ) -> None:
        start_hilight = _ANSI.COLOR_FAILED if want_color_output() else ""
        stop_hilight = _ANSI.COLOR_DEFAULT if want_color_output() else ""
        if msg is None:
            rest = ""
        else:
            rest = f": {msg}"
        self.log.info(
            "%s %sfailed%s%s",
            self._test.fullname,
            start_hilight,
            stop_hilight,
            rest,
            exc_info=result,
        )

        # write out xunit results
        ratio_time = self._safe_divide(sim_time_ns, wall_time_s)
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
            message=f"Test failed with RANDOM_SEED={cocotb._random_seed}"
        )

        # update running passed/failed/skipped counts
        self.failures += 1
        self.count += 1

        # save details for summary
        self._test_results.append(
            {
                "test": self._test.fullname,
                "pass": False,
                "sim": sim_time_ns,
                "real": wall_time_s,
                "ratio": ratio_time,
            }
        )

    def _record_sim_failure(self) -> None:
        if self._test._expect_sim_failure:
            self._record_test_passed(
                wall_time_s=0,
                sim_time_ns=0,
                result=None,
                msg=f"simulator failed as expected with: {self._sim_failure!s}",
            )
        else:
            self._record_test_failed(
                wall_time_s=0,
                sim_time_ns=0,
                result=self._sim_failure,
                msg=None,
            )

    def _log_test_summary(self) -> None:
        """Called by :meth:`_tear_down` to log the test summary."""
        real_time = time.time() - self._regression_start_time
        sim_time_ns = get_sim_time("ns")
        ratio_time = self._safe_divide(sim_time_ns, real_time)

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
            len(max([x["test"] for x in self._test_results], key=len)),
        )
        RESULT_FIELD_LEN = len(RESULT_FIELD)
        SIM_FIELD_LEN = len(SIM_FIELD)
        REAL_FIELD_LEN = len(REAL_FIELD)
        RATIO_FIELD_LEN = len(RATIO_FIELD)

        header_dict = dict(
            a=TEST_FIELD,
            b=RESULT_FIELD,
            c=SIM_FIELD,
            d=REAL_FIELD,
            e=RATIO_FIELD,
            a_len=TEST_FIELD_LEN,
            b_len=RESULT_FIELD_LEN,
            c_len=SIM_FIELD_LEN,
            d_len=REAL_FIELD_LEN,
            e_len=RATIO_FIELD_LEN,
        )

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

            if result["pass"] is None:
                ratio = "-.--"
                pass_fail_str = "SKIP"
                if want_color_output():
                    hilite = _ANSI.COLOR_SKIPPED
                    lolite = _ANSI.COLOR_DEFAULT
            elif result["pass"]:
                ratio = format(result["ratio"], "0.2f")
                pass_fail_str = "PASS"
                if want_color_output():
                    hilite = _ANSI.COLOR_PASSED
                    lolite = _ANSI.COLOR_DEFAULT
            else:
                ratio = format(result["ratio"], "0.2f")
                pass_fail_str = "FAIL"
                if want_color_output():
                    hilite = _ANSI.COLOR_FAILED
                    lolite = _ANSI.COLOR_DEFAULT

            test_dict = dict(
                a=result["test"],
                b=pass_fail_str,
                c=result["sim"],
                d=result["real"],
                e=ratio,
                a_len=TEST_FIELD_LEN,
                b_len=RESULT_FIELD_LEN,
                c_len=SIM_FIELD_LEN - 1,
                d_len=REAL_FIELD_LEN - 1,
                e_len=RATIO_FIELD_LEN - 1,
                start=hilite,
                end=lolite,
            )

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
        self._sim_failure = SimFailure(msg)
        cocotb._scheduler_inst._abort_test(self._sim_failure)
        cocotb._scheduler_inst._handle_termination()

    @staticmethod
    def _safe_divide(a: float, b: float) -> float:
        """Used when computing time ratios to ensure no exception is raised if either time is 0."""
        try:
            return a / b
        except ZeroDivisionError:
            if a == 0:
                return float("nan")
            else:
                return float("inf")


F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, None]])


class TestFactory(Generic[F]):
    """Factory to automatically generate tests.

    Args:
        test_function: A Callable that returns the test Coroutine.
            Must take *dut* as the first argument.
        *args: Remaining arguments are passed directly to the test function.
            Note that these arguments are not varied. An argument that
            varies with each test must be a keyword argument to the
            test function.
        **kwargs: Remaining keyword arguments are passed directly to the test function.
            Note that these arguments are not varied. An argument that
            varies with each test must be a keyword argument to the
            test function.

    Assuming we have a common test function that will run a test. This test
    function will take keyword arguments (for example generators for each of
    the input interfaces) and generate tests that call the supplied function.

    This Factory allows us to generate sets of tests based on the different
    permutations of the possible arguments to the test function.

    For example, if we have a module that takes backpressure, has two configurable
    features where enabling ``feature_b`` requires ``feature_a`` to be active, and
    need to test against data generation routines ``gen_a`` and ``gen_b``:

    >>> tf = TestFactory(test_function=run_test)
    >>> tf.add_option(name="data_in", optionlist=[gen_a, gen_b])
    >>> tf.add_option("backpressure", [None, random_backpressure])
    >>> tf.add_option(
    ...     ("feature_a", "feature_b"), [(False, False), (True, False), (True, True)]
    ... )
    >>> tf.generate_tests()

    We would get the following tests:

        * ``gen_a`` with no backpressure and both features disabled
        * ``gen_a`` with no backpressure and only ``feature_a`` enabled
        * ``gen_a`` with no backpressure and both features enabled
        * ``gen_a`` with ``random_backpressure`` and both features disabled
        * ``gen_a`` with ``random_backpressure`` and only ``feature_a`` enabled
        * ``gen_a`` with ``random_backpressure`` and both features enabled
        * ``gen_b`` with no backpressure and both features disabled
        * ``gen_b`` with no backpressure and only ``feature_a`` enabled
        * ``gen_b`` with no backpressure and both features enabled
        * ``gen_b`` with ``random_backpressure`` and both features disabled
        * ``gen_b`` with ``random_backpressure`` and only ``feature_a`` enabled
        * ``gen_b`` with ``random_backpressure`` and both features enabled

    The tests are appended to the calling module for auto-discovery.

    Tests are simply named ``test_function_N``. The docstring for the test (hence
    the test description) includes the name and description of each generator.

    .. versionchanged:: 1.5
        Groups of options are now supported

    .. versionchanged:: 2.0
        You can now pass :func:`cocotb.test` decorator arguments when generating tests.

    .. deprecated:: 2.0
        Use :func:`cocotb.parameterize` instead.
    """

    def __init__(self, test_function: F, *args: Any, **kwargs: Any) -> None:
        warnings.warn(
            "TestFactory is deprecated, use `@cocotb.parameterize` instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self.test_function = test_function
        self.args = args
        self.kwargs_constant = kwargs
        self.kwargs: Dict[
            Union[str, Sequence[str]], Union[Sequence[Any], Sequence[Sequence[Any]]]
        ] = {}

    @overload
    def add_option(self, name: str, optionlist: Sequence[Any]) -> None: ...

    @overload
    def add_option(
        self, name: Sequence[str], optionlist: Sequence[Sequence[Any]]
    ) -> None: ...

    def add_option(
        self,
        name: Union[str, Sequence[str]],
        optionlist: Union[Sequence[str], Sequence[Sequence[str]]],
    ) -> None:
        """Add a named option to the test.

        Args:
            name:
                An option name, or an iterable of several option names. Passed to test as keyword arguments.

            optionlist:
                A list of possible options for this test knob.
                If N names were specified, this must be a list of N-tuples or
                lists, where each element specifies a value for its respective
                option.

        .. versionchanged:: 1.5
            Groups of options are now supported
        """
        if not isinstance(name, str):
            for opt in optionlist:
                if len(name) != len(opt):
                    raise ValueError(
                        "Mismatch between number of options and number of option values in group"
                    )
        self.kwargs[name] = optionlist

    def generate_tests(
        self,
        *,
        prefix: Optional[str] = None,
        postfix: Optional[str] = None,
        name: Optional[str] = None,
        timeout_time: Optional[float] = None,
        timeout_unit: str = "steps",
        expect_fail: bool = False,
        expect_error: Union[Type[Exception], Sequence[Type[Exception]]] = (),
        skip: bool = False,
        stage: int = 0,
        _expect_sim_failure: bool = False,
    ) -> None:
        """
        Generate an exhaustive set of tests using the cartesian product of the
        possible keyword arguments.

        The generated tests are appended to the namespace of the calling
        module.

        Args:
            prefix:
                Text string to append to start of ``test_function`` name when naming generated test cases.
                This allows reuse of a single ``test_function`` with multiple :class:`TestFactories <.TestFactory>` without name clashes.

                .. deprecated:: 2.0
                    Use the more flexible ``name`` field instead.

            postfix:
                Text string to append to end of ``test_function`` name when naming generated test cases.
                This allows reuse of a single ``test_function`` with multiple :class:`TestFactories <.TestFactory>` without name clashes.

                .. deprecated:: 2.0
                    Use the more flexible ``name`` field instead.

            name:
                Passed as ``name`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            timeout_time:
                Passed as ``timeout_time`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            timeout_unit:
                Passed as ``timeout_unit`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            expect_fail:
                Passed as ``expect_fail`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            expect_error:
                Passed as ``expect_error`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            skip:
                Passed as ``skip`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0

            stage:
                Passed as ``stage`` argument to :func:`cocotb.test`.

                .. versionadded:: 2.0
        """

        if prefix is not None:
            warnings.warn(
                "``prefix`` argument is deprecated. Use the more flexible ``name`` field instead.",
                DeprecationWarning,
            )
        else:
            prefix = ""

        if postfix is not None:
            warnings.warn(
                "``postfix`` argument is deprecated. Use the more flexible ``name`` field instead.",
                DeprecationWarning,
            )
        else:
            postfix = ""

        glbs = inspect.currentframe().f_back.f_globals

        if "__cocotb_tests__" not in glbs:
            glbs["__cocotb_tests__"] = []

        test_func_name = self.test_function.__qualname__ if name is None else name

        for index, testoptions in enumerate(
            dict(zip(self.kwargs, v)) for v in product(*self.kwargs.values())
        ):
            name = "%s%s%s_%03d" % (
                prefix,
                test_func_name,
                postfix,
                index + 1,
            )
            doc: str = "Automatically generated test\n\n"

            # preprocess testoptions to split tuples
            testoptions_split: Dict[str, Sequence[Any]] = {}
            for optname, optvalue in testoptions.items():
                if isinstance(optname, str):
                    optvalue = cast(Sequence[Any], optvalue)
                    testoptions_split[optname] = optvalue
                else:
                    # previously checked in add_option; ensure nothing has changed
                    optvalue = cast(Sequence[Sequence[Any]], optvalue)
                    assert len(optname) == len(optvalue)
                    for n, v in zip(optname, optvalue):
                        testoptions_split[n] = v

            for optname, optvalue in testoptions_split.items():
                if callable(optvalue):
                    if not optvalue.__doc__:
                        desc = "No docstring supplied"
                    else:
                        desc = optvalue.__doc__.split("\n")[0]
                    doc += f"\t{optname}: {optvalue.__qualname__} ({desc})\n"
                else:
                    doc += f"\t{optname}: {repr(optvalue)}\n"

            kwargs: Dict[str, Any] = {}
            kwargs.update(self.kwargs_constant)
            kwargs.update(testoptions_split)

            @functools.wraps(self.test_function)
            async def _my_test(dut, kwargs: Dict[str, Any] = kwargs) -> None:
                await self.test_function(dut, *self.args, **kwargs)

            _my_test.__doc__ = doc
            _my_test.__name__ = name
            _my_test.__qualname__ = name

            if name in glbs:
                _logger.error(
                    "Overwriting %s in module %s. "
                    "This causes a previously defined testcase not to be run. "
                    "Consider using the `name`, `prefix`, or `postfix` arguments to augment the name.",
                    name,
                    glbs["__name__"],
                )

            test = Test(
                func=_my_test,
                name=name,
                module=glbs["__name__"],
                timeout_time=timeout_time,
                timeout_unit=timeout_unit,
                expect_fail=expect_fail,
                expect_error=expect_error,
                skip=skip,
                stage=stage,
                _expect_sim_failure=_expect_sim_failure,
            )

            glbs["__cocotb_tests__"].append(test)
            glbs[test.name] = test
