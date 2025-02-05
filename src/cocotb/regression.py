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
from enum import auto
from importlib import import_module
from typing import (
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

import cocotb
import cocotb._init
import cocotb._write_scheduler
import cocotb.event_loop
import cocotb.task
from cocotb import _ANSI, simulator
from cocotb._exceptions import InternalError
from cocotb._outcomes import Error, Outcome
from cocotb._py_compat import cached_property
from cocotb._utils import (
    DocEnum,
    remove_traceback_frames,
    safe_divide,
    want_color_output,
)
from cocotb._xunit_reporter import XUnitReporter
from cocotb.result import TestSuccess
from cocotb.task import ResultType, Task
from cocotb.triggers import NullTrigger, SimTimeoutError, Timer, with_timeout
from cocotb.utils import get_sim_time

_pdb_on_exception = "COCOTB_PDB_ON_EXCEPTION" in os.environ

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


class _SimFailure(Exception):
    """A Test failure due to simulator failure."""

    __name__ = "SimFailure"
    __qualname__ = "SimFailure"


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
            If ``True`` and the test fails a functional check via an :keyword:`assert` statement, :func:`pytest.raises`,
            :func:`pytest.warns`, or :func:`pytest.deprecated_call`, the test is considered to have passed.
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
        expect_error: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = (),
        skip: bool = False,
        stage: int = 0,
        _expect_sim_failure: bool = False,
    ) -> None:
        self.func: Callable[..., Coroutine[Any, Any, None]]
        if timeout_time is not None:
            co = func  # must save ref because we overwrite variable "func"

            @functools.wraps(func)
            async def f(*args: object, **kwargs: object) -> None:
                running_co = Task(co(*args, **kwargs))

                try:
                    await with_timeout(running_co, timeout_time, timeout_unit)
                except SimTimeoutError:
                    running_co.kill()
                    raise

            self.func = f
        else:
            self.func = func
        self.timeout_time = timeout_time
        self.timeout_unit = timeout_unit
        self.expect_fail = expect_fail
        if isinstance(expect_error, type):
            expect_error = (expect_error,)
        if _expect_sim_failure:
            expect_error += (_SimFailure,)
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


def _get_lineno(func: Any) -> int:
    try:
        return inspect.getsourcelines(func)[1]
    except Exception:
        return 1


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
        self._test_outcome: Union[None, Outcome[Any]]
        self._test_start_time: float
        self._test_start_sim_time: float
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
        self._sim_failure: Union[_SimFailure, None] = None

        # Setup XUnit
        ###################

        results_filename = os.getenv("COCOTB_RESULTS_FILE", "results.xml")
        suite_name = os.getenv("COCOTB_RESULT_TESTSUITE", "all")
        package_name = os.getenv("COCOTB_RESULT_TESTPACKAGE", "all")

        self.xunit = XUnitReporter(filename=results_filename)
        self.xunit.add_testsuite(name=suite_name, package=package_name)
        self.xunit.add_property(name="random_seed", value=str(cocotb._random_seed))

    @cached_property
    def log(self) -> logging.Logger:
        return logging.getLogger(__name__)

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

    def setup_pytest_assertion_rewriting(self) -> None:
        """Configure pytest to rewrite assertions for better failure messages.

        Must be called before all modules containing tests are imported.
        """
        try:
            import pytest
        except ImportError:
            self.log.info(
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
            self.log.exception(
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
                self._test_task = _TestTask(
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

            self._test_outcome = None
            self._test_start_sim_time = get_sim_time("ns")
            self._test_start_time = time.time()

            if self._first_test:
                self._first_test = False
                return self._schedule_next_test()
            else:
                _ = self._timer1.register(self._schedule_next_test)
                # We don't plan on cancelling this, so we toss the handle
                return

        return self._finalize_regression()

    def _schedule_next_test(self) -> None:
        self._test_task._schedule_resume()
        cocotb.event_loop._instance.run()

    def _fail_simulation(self, msg: str) -> None:
        self._sim_failure = _SimFailure(msg)
        self._end_test(Error(self._sim_failure))

    def _end_test(self, outcome: Outcome[Any]) -> None:
        # set test outcome
        if self._test_outcome is not None:  # pragma: no cover
            raise InternalError("Outcome already has a value, but is being set again.")
        self._test_outcome = outcome

        # cancel all remaining tasks
        for task in cocotb.task.all_tasks():
            task.cancel()

        # set up test finalization callback after all tasks have been cancelled
        cocotb.event_loop._instance.schedule(self._finalize_test)

    def _finalize_test(self) -> None:
        self._record_test_outcome()
        return self._execute()

    def _finalize_regression(self) -> None:
        """Called by :meth:`_execute` when there are no more tests to run to finalize the regression."""
        if self._test_queue:  # pragma: no cover
            raise InternalError("Finalizing RegressionManager with tests remaining")

        self._log_test_summary()
        self.xunit.write()
        simulator.stop_simulator()
        cocotb._init._shutdown_testbench()

    def _test_done_callback(self, task: Task[Any]) -> None:
        self._end_test(cast(Outcome[Any], task._result))

    def _task_done_callback(self, task: Task[Any]) -> None:
        # if cancelled, do nothing
        if task.cancelled():
            return
        # if no failure, do nothing
        e = task.exception()
        if e is None:
            return
        # if there are watchers, let the exception propagate
        breakpoint()
        if task.complete._callbacks:
            return
        # there was a failure and no one is watching, fail test
        elif isinstance(e, (TestSuccess, AssertionError)):
            task.log.info("Test stopped by this task")
            self._end_test(Error(e))
        else:
            task.log.error("Exception raised by this task")
            self._end_test(Error(e))

    def _record_test_outcome(self) -> None:
        """Callback given to the scheduler, to be called when the current test completes.

        Due to the way that simulation failure is handled,
        this function must be able to detect simulation failure and finalize the regression.
        """

        # compute test completion time
        wall_time_s = time.time() - self._test_start_time
        sim_time_ns = get_sim_time("ns") - self._test_start_sim_time
        test = self._test

        # score test
        if self._test_outcome is None:  # pragma: no cover
            raise InternalError("Test completed without setting outcome")
        try:
            self._test_outcome.get()
        except BaseException as e:
            result = remove_traceback_frames(e, ["_record_test_outcome", "get"])
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
        lineno = _get_lineno(self._test.func)
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
        lineno = _get_lineno(self._test.func)
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
        lineno = _get_lineno(self._test.func)
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
                "ratio": safe_divide(0, 0),
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
        ratio_time = safe_divide(sim_time_ns, wall_time_s)
        lineno = _get_lineno(self._test.func)
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
        result: Union[BaseException, None],
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
        ratio_time = safe_divide(sim_time_ns, wall_time_s)
        lineno = _get_lineno(self._test.func)
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


# TODO Make this not a global singleton
# TODO Use normal type annotations once we're on Python 3.8
_instance = None  # type: Union[RegressionManager, None]


def get_regression_manager() -> RegressionManager:
    if _instance is None:
        raise RuntimeError("No RegressionManager is available")
    return _instance


class _TestTask(Task[None]):
    """Specialized Task for running tests.

    Overrides the name to include "Test" and adds hook for informing the
    regression manager when the test is complete.
    """

    def __init__(self, inst: Coroutine[Any, Any, None], name: str) -> None:
        super().__init__(inst)
        self.name = f"Test {name}"
        self._add_done_callback(get_regression_manager()._test_done_callback)


def start_soon(
    coro: Union[Task[ResultType], Coroutine[Any, Any, ResultType]],
) -> Task[ResultType]:
    """
    Schedule a coroutine to be run concurrently in a :class:`~Task`.

    Note that this is not an :keyword:`async` function,
    and the new task will not execute until the calling task yields control.

    Args:
        coro: A task or coroutine to be run.

    Returns:
        The :class:`~Task` that is scheduled to be run.

    .. versionadded:: 1.6
    """
    task = create_task(coro)
    task._schedule_resume()
    return task


async def start(
    coro: Union[Task[ResultType], Coroutine[Any, Any, ResultType]],
) -> Task[ResultType]:
    """
    Schedule a coroutine to be run concurrently, then yield control to allow pending tasks to execute.

    The calling task will resume execution before control is returned to the simulator.

    When the calling task resumes, the newly scheduled task may have completed,
    raised an Exception, or be pending on a :class:`~cocotb.triggers.Trigger`.

    Args:
        coro: A task or coroutine to be run.

    Returns:
        The :class:`~Task` that has been scheduled and allowed to execute.

    .. versionadded:: 1.6
    """
    task = start_soon(coro)
    await NullTrigger()
    return task


def create_task(
    coro: Union[Task[ResultType], Coroutine[Any, Any, ResultType]],
) -> Task[ResultType]:
    """
    Construct a coroutine into a :class:`~Task` without scheduling the task.

    The task can later be scheduled with :func:`cocotb.start` or :func:`cocotb.start_soon`.

    Args:
        coro: An existing task or a coroutine to be wrapped.

    Returns:
        Either the provided :class:`~Task` or a new Task wrapping the coroutine.

    .. versionadded:: 1.6
    """
    if isinstance(coro, Task):
        return coro
    elif isinstance(coro, Coroutine):
        task = Task[ResultType](coro)
        task._add_done_callback(get_regression_manager()._task_done_callback)
        return task
    elif inspect.iscoroutinefunction(coro):
        raise TypeError(
            f"Coroutine function {coro} should be called prior to being scheduled."
        )
    elif inspect.isasyncgen(coro):
        raise TypeError(
            f"{coro.__qualname__} is an async generator, not a coroutine. "
            "You likely used the yield keyword instead of await."
        )
    else:
        raise TypeError(
            f"Attempt to add an object of type {type(coro)} to the scheduler, "
            f"which isn't a coroutine: {coro!r}\n"
        )
