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

import hashlib
import inspect
import math
import os
import pdb
import random
import sys
import time
import traceback
from itertools import product
from typing import Any, Iterable, Optional, Tuple, Type

import cocotb
import cocotb.ANSI as ANSI
from cocotb import simulator
from cocotb._deprecation import deprecated
from cocotb.decorators import test as Test
from cocotb.handle import SimHandle
from cocotb.log import SimLog
from cocotb.outcomes import Error, Outcome
from cocotb.result import SimFailure, TestSuccess
from cocotb.task import Task
from cocotb.utils import get_sim_time, remove_traceback_frames, want_color_output
from cocotb.xunit_reporter import XUnitReporter

_pdb_on_exception = "COCOTB_PDB_ON_EXCEPTION" in os.environ

# Optional support for coverage collection of testbench files
coverage = None
if "COVERAGE" in os.environ:
    try:
        import coverage
    except ImportError as e:
        msg = (
            "Coverage collection requested but coverage module not available"
            "\n"
            "Import error was: %s\n" % repr(e)
        )
        sys.stderr.write(msg)


def _my_import(name: str) -> Any:
    mod = __import__(name)
    components = name.split(".")
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


_logger = SimLog(__name__)

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
        assert "pytest.raises doesn't raise an exception when it fails"


class RegressionManager:
    """Encapsulates all regression capability into a single place"""

    def __init__(self, dut: SimHandle, tests: Iterable[Test]):
        """
        Args:
            dut (SimHandle): The root handle to pass into test functions.
            tests (Iterable[Test]): tests to run
        """
        self._dut = dut
        self._test = None
        self._test_task = None
        self._test_start_time = None
        self._test_start_sim_time = None
        self._cov = None
        self.log = _logger
        self.start_time = time.time()
        self.test_results = []
        self.count = 0
        self.passed = 0
        self.skipped = 0
        self.failures = 0
        self._tearing_down = False

        # Setup XUnit
        ###################

        results_filename = os.getenv("COCOTB_RESULTS_FILE", "results.xml")
        suite_name = os.getenv("RESULT_TESTSUITE", "all")
        package_name = os.getenv("RESULT_TESTPACKAGE", "all")

        self.xunit = XUnitReporter(filename=results_filename)

        self.xunit.add_testsuite(name=suite_name, package=package_name)

        self.xunit.add_property(name="random_seed", value=str(cocotb.RANDOM_SEED))

        # Setup Coverage
        ####################

        if coverage is not None:
            self.log.info("Enabling coverage collection of Python code")
            config_filepath = os.getenv("COVERAGE_RCFILE")
            if config_filepath is None:
                # Exclude cocotb itself from coverage collection.
                cocotb_package_dir = os.path.dirname(__file__)
                self._cov = coverage.coverage(
                    branch=True, omit=[f"{cocotb_package_dir}/*"]
                )
            else:
                # Allow the config file to handle all configuration
                self._cov = coverage.coverage()
            self._cov.start()

        # Test Discovery
        ####################
        self._queue = []
        for test in tests:
            self.log.info(f"Found test {test.__module__}.{test.__qualname__}")
            self._queue.append(test)
        self.ntests = len(self._queue)

        if not self._queue:
            self.log.warning("No tests were discovered")

        self._queue.sort(key=lambda test: (test.stage, test._id))

    @classmethod
    def from_discovery(cls, dut: SimHandle):
        """
        Obtains the test list by discovery.

        See :envvar:`MODULE` and :envvar:`TESTCASE` for details on how tests are discovered.

        Args:
            dut (SimHandle): The root handle to pass into test functions.
        """
        tests = cls._discover_tests()
        return cls(dut, tests)

    @classmethod
    def _discover_tests(cls) -> Iterable[Test]:
        """
        Discovers tests in files automatically.

        See :envvar:`MODULE` and :envvar:`TESTCASE` for details on how tests are discovered.
        """
        module_str = os.getenv("MODULE")
        test_str = os.getenv("TESTCASE")

        if module_str is None:
            raise ValueError(
                "Environment variable MODULE, which defines the module(s) to execute, is not defined."
            )

        modules = [s.strip() for s in module_str.split(",") if s.strip()]

        cls._setup_pytest_assertion_rewriting(modules)

        tests = None
        if test_str:
            tests = [s.strip() for s in test_str.split(",") if s.strip()]

        for module_name in modules:
            try:
                _logger.debug("Python Path: " + ",".join(sys.path))
                _logger.debug("PWD: " + os.getcwd())
                module = _my_import(module_name)
            except Exception as E:
                _logger.critical("Failed to import module %s: %s", module_name, E)
                _logger.info('MODULE variable was "%s"', ".".join(modules))
                _logger.info("Traceback: ")
                _logger.info(traceback.format_exc())
                raise

            if tests is not None:
                not_found_tests = []
                # Specific functions specified, don't auto-discover
                for test_name in tests:
                    try:
                        test = getattr(module, test_name)
                    except AttributeError:
                        not_found_tests.append(test_name)
                        continue

                    if not isinstance(test, Test):
                        _logger.error(
                            "Requested %s from module %s isn't a cocotb.test decorated coroutine",
                            test_name,
                            module_name,
                        )
                        raise ImportError(
                            "Failed to find requested test %s" % test_name
                        )

                    # If we request a test manually, it should be run even if skip=True is set.
                    test.skip = False

                    yield test

                # Use the non-matching test names in the next module search
                tests = not_found_tests

            else:
                # auto-discover
                for thing in vars(module).values():
                    if isinstance(thing, Test):
                        yield thing

        # If any test were not found in any module, raise an error
        if tests:
            _logger.error(
                "Requested test(s) %s wasn't found in module(s) %s", tests, modules
            )
            raise AttributeError("Test(s) %s doesn't exist in %s" % (tests, modules))

    @classmethod
    def _setup_pytest_assertion_rewriting(cls, test_modules: Iterable[str]) -> None:
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
                "Configuring the assertion rewrite hook using pytest {} failed. "
                "Please file a bug report!".format(pytest.__version__)
            )

    @deprecated("This method is now private.")
    def tear_down(self) -> None:
        self._tear_down()

    def _tear_down(self) -> None:
        # prevent re-entering the tear down procedure
        if not self._tearing_down:
            self._tearing_down = True
        else:
            return

        # fail remaining tests
        while True:
            test = self._next_test()
            if test is None:
                break
            self._record_result(
                test=test, outcome=Error(SimFailure), wall_time_s=0, sim_time_ns=0
            )

        # Write out final log messages
        self._log_test_summary()

        # Generate output reports
        self.xunit.write()
        if self._cov:
            self._cov.stop()
            self.log.info("Writing coverage data")
            self._cov.save()
            self._cov.html_report()
        if cocotb._library_coverage is not None:
            # TODO: move this once we have normal shutdown behavior to _sim_event
            cocotb._library_coverage.stop()
            cocotb._library_coverage.save()

        # Setup simulator finalization
        simulator.stop_simulator()

    @deprecated("This method is now private.")
    def next_test(self) -> Optional[Test]:
        return self._next_test()

    def _next_test(self) -> Optional[Test]:
        """Get the next test to run"""
        if not self._queue:
            return None
        self.count += 1
        return self._queue.pop(0)

    @deprecated("This method is now private.")
    def handle_result(self, test: Task) -> None:
        self._handle_result(test)

    def _handle_result(self, test: Task) -> None:
        """Handle a test completing.

        Dump result to XML and schedule the next test (if any). Entered by the scheduler.

        Args:
            test: The test that completed
        """
        assert test is self._test_task

        real_time = time.time() - self._test_start_time
        sim_time_ns = get_sim_time("ns") - self._test_start_sim_time

        self._record_result(
            test=self._test,
            outcome=self._test_task._outcome,
            wall_time_s=real_time,
            sim_time_ns=sim_time_ns,
        )

        self._execute()

    def _init_test(self, test: Test) -> Optional[Task]:
        """Initialize a test.

        Record outcome if the initialization fails.
        Record skip if the test is skipped.
        Save the initialized test if it successfully initializes.
        """

        if test.skip:
            hilight_start = ANSI.COLOR_SKIPPED if want_color_output() else ""
            hilight_end = ANSI.COLOR_DEFAULT if want_color_output() else ""
            # Want this to stand out a little bit
            self.log.info(
                "{start}skipping{end} {name} ({i}/{total})".format(
                    start=hilight_start,
                    i=self.count,
                    total=self.ntests,
                    end=hilight_end,
                    name=test.__qualname__,
                )
            )
            self._record_result(test, None, 0, 0)
            return None

        test_init_outcome = cocotb.outcomes.capture(test, self._dut)

        if isinstance(test_init_outcome, cocotb.outcomes.Error):
            self.log.error(
                "Failed to initialize test %s" % test.__qualname__,
                exc_info=test_init_outcome.error,
            )
            self._record_result(test, test_init_outcome, 0, 0)
            return None

        running_test = test_init_outcome.get()

        # seed random number generator based on test module, name, and RANDOM_SEED
        hasher = hashlib.sha1()
        hasher.update(test.__qualname__.encode())
        hasher.update(test.__module__.encode())
        seed = cocotb.RANDOM_SEED + int(hasher.hexdigest(), 16)
        random.seed(seed)

        return running_test

    def _score_test(self, test: Test, outcome: Outcome) -> Tuple[bool, bool]:
        """
        Given a test and the test's outcome, determine if the test met expectations and log pertinent information
        """

        # scoring outcomes
        result_pass = True
        sim_failed = False

        try:
            outcome.get()
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as e:
            result = remove_traceback_frames(e, ["_score_test", "get"])
        else:
            result = TestSuccess()

        if (
            isinstance(result, TestSuccess)
            and not test.expect_fail
            and not test.expect_error
        ):
            self._log_test_passed(test, None, None)

        elif isinstance(result, TestSuccess) and test.expect_error:
            self._log_test_failed(test, None, "passed but we expected an error")
            result_pass = False

        elif isinstance(result, TestSuccess):
            self._log_test_failed(test, None, "passed but we expected a failure")
            result_pass = False

        elif isinstance(result, SimFailure):
            if isinstance(result, test.expect_error):
                self._log_test_passed(test, result, "errored as expected")
            else:
                self.log.error("Test error has lead to simulator shutting us down")
                result_pass = False
            # whether we expected it or not, the simulation has failed unrecoverably
            sim_failed = True

        elif isinstance(result, (AssertionError, _Failed)) and test.expect_fail:
            self._log_test_passed(test, result, "failed as expected")

        elif test.expect_error:
            if isinstance(result, test.expect_error):
                self._log_test_passed(test, result, "errored as expected")
            else:
                self._log_test_failed(test, result, "errored with unexpected type ")
                result_pass = False

        else:
            self._log_test_failed(test, result, None)
            result_pass = False

            if _pdb_on_exception:
                pdb.post_mortem(result.__traceback__)

        return result_pass, sim_failed

    def _log_test_passed(
        self, test: Test, result: Optional[Exception] = None, msg: Optional[str] = None
    ) -> None:
        start_hilight = ANSI.COLOR_PASSED if want_color_output() else ""
        stop_hilight = ANSI.COLOR_DEFAULT if want_color_output() else ""
        if msg is None:
            rest = ""
        else:
            rest = f": {msg}"
        if result is None:
            result_was = ""
        else:
            result_was = f" (result was {type(result).__qualname__})"
        self.log.info(
            f"{test.__qualname__} {start_hilight}passed{stop_hilight}{rest}{result_was}"
        )

    def _log_test_failed(
        self, test: Test, result: Optional[Exception] = None, msg: Optional[str] = None
    ) -> None:
        start_hilight = ANSI.COLOR_FAILED if want_color_output() else ""
        stop_hilight = ANSI.COLOR_DEFAULT if want_color_output() else ""
        if msg is None:
            rest = ""
        else:
            rest = f": {msg}"
        self.log.info(
            f"{test.__qualname__} {start_hilight}failed{stop_hilight}{rest}",
            exc_info=result,
        )

    def _record_result(
        self,
        test: Test,
        outcome: Optional[Outcome],
        wall_time_s: float,
        sim_time_ns: float,
    ) -> None:

        ratio_time = self._safe_divide(sim_time_ns, wall_time_s)
        try:
            lineno = inspect.getsourcelines(test._func)[1]
        except OSError:
            lineno = 1

        self.xunit.add_testcase(
            name=test.__qualname__,
            classname=test.__module__,
            file=inspect.getfile(test._func),
            lineno=repr(lineno),
            time=repr(wall_time_s),
            sim_time_ns=repr(sim_time_ns),
            ratio_time=repr(ratio_time),
        )

        if outcome is None:  # skipped
            test_pass, sim_failed = None, False
            self.xunit.add_skipped()
            self.skipped += 1

        else:
            test_pass, sim_failed = self._score_test(test, outcome)
            if not test_pass:
                self.xunit.add_failure(
                    message=f"Test failed with RANDOM_SEED={cocotb.RANDOM_SEED}"
                )
                self.failures += 1
            else:
                self.passed += 1

        self.test_results.append(
            {
                "test": ".".join([test.__module__, test.__qualname__]),
                "pass": test_pass,
                "sim": sim_time_ns,
                "real": wall_time_s,
                "ratio": ratio_time,
            }
        )

        if sim_failed:
            self._tear_down()
            return

    @deprecated("This method is now private.")
    def execute(self) -> None:
        self._execute()

    def _execute(self) -> None:
        while True:
            self._test = self._next_test()
            if self._test is None:
                return self._tear_down()

            self._test_task = self._init_test(self._test)
            if self._test_task is not None:
                return self._start_test()

    def _start_test(self) -> None:
        # Want this to stand out a little bit
        start = ""
        end = ""
        if want_color_output():
            start = ANSI.COLOR_TEST
            end = ANSI.COLOR_DEFAULT
        self.log.info(
            "{start}running{end} {name} ({i}/{total}){description}".format(
                start=start,
                i=self.count,
                total=self.ntests,
                end=end,
                name=self._test.__qualname__,
                description=_trim(self._test.__doc__),
            )
        )

        self._test_start_time = time.time()
        self._test_start_sim_time = get_sim_time("ns")
        cocotb.scheduler._add_test(self._test_task)

    def _log_test_summary(self) -> None:

        real_time = time.time() - self.start_time
        sim_time_ns = get_sim_time("ns")
        ratio_time = self._safe_divide(sim_time_ns, real_time)

        if len(self.test_results) == 0:
            return

        TEST_FIELD = "TEST"
        RESULT_FIELD = "STATUS"
        SIM_FIELD = "SIM TIME (ns)"
        REAL_FIELD = "REAL TIME (s)"
        RATIO_FIELD = "RATIO (ns/s)"
        TOTAL_NAME = f"TESTS={self.ntests} PASS={self.passed} FAIL={self.failures} SKIP={self.skipped}"

        TEST_FIELD_LEN = max(
            len(TEST_FIELD),
            len(TOTAL_NAME),
            len(max([x["test"] for x in self.test_results], key=len)),
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
        for result in self.test_results:
            hilite = ""
            lolite = ""

            if result["pass"] is None:
                ratio = "-.--"
                pass_fail_str = "SKIP"
                if want_color_output():
                    hilite = ANSI.COLOR_SKIPPED
                    lolite = ANSI.COLOR_DEFAULT
            elif result["pass"]:
                ratio = format(result["ratio"], "0.2f")
                pass_fail_str = "PASS"
                if want_color_output():
                    hilite = ANSI.COLOR_PASSED
                    lolite = ANSI.COLOR_DEFAULT
            else:
                ratio = format(result["ratio"], "0.2f")
                pass_fail_str = "FAIL"
                if want_color_output():
                    hilite = ANSI.COLOR_FAILED
                    lolite = ANSI.COLOR_DEFAULT

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

    @staticmethod
    def _safe_divide(a: float, b: float) -> float:
        try:
            return a / b
        except ZeroDivisionError:
            if a == 0:
                return float("nan")
            else:
                return float("inf")


def _create_test(function, name, documentation, mod, *args, **kwargs):
    """Factory function to create tests, avoids late binding.

    Creates a test dynamically.  The test will call the supplied
    function with the supplied arguments.

    Args:
        function (function):  The test function to run.
        name (str):           The name of the test.
        documentation (str):  The docstring for the test.
        mod (module):         The module this function belongs to.
        *args:                Remaining args to pass to test function.
        **kwargs:             Passed to the test function.

    Returns:
        Decorated test function
    """

    async def _my_test(dut):
        await function(dut, *args, **kwargs)

    _my_test.__name__ = name
    _my_test.__qualname__ = name
    _my_test.__doc__ = documentation
    _my_test.__module__ = mod.__name__

    return cocotb.test()(_my_test)


class TestFactory:
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
    >>> tf.add_option(name='data_in', optionlist=[gen_a, gen_b])
    >>> tf.add_option('backpressure', [None, random_backpressure])
    >>> tf.add_option(('feature_a', 'feature_b'), [(False, False), (True, False), (True, True)])
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
    """

    # Prevent warnings from collection of TestFactories by unit testing frameworks.
    __test__ = False

    def __init__(self, test_function, *args, **kwargs):
        self.test_function = test_function
        self.name = self.test_function.__qualname__

        self.args = args
        self.kwargs_constant = kwargs
        self.kwargs = {}
        self.log = _logger

    def add_option(self, name, optionlist):
        """Add a named option to the test.

        Args:
            name (str or iterable of str): An option name, or an iterable of
                several option names.  Passed to test as keyword arguments.

            optionlist (list): A list of possible options for this test knob.
                If N names were specified, this must be a list of N-tuples or
                lists, where each element specifies a value for its respective
                option.

        .. versionchanged:: 1.5
            Groups of options are now supported
        """
        if not isinstance(name, str):
            name = tuple(name)
            for opt in optionlist:
                if len(name) != len(opt):
                    raise ValueError(
                        "Mismatch between number of options and number of option values in group"
                    )
        self.kwargs[name] = optionlist

    def generate_tests(self, prefix="", postfix=""):
        """
        Generate an exhaustive set of tests using the cartesian product of the
        possible keyword arguments.

        The generated tests are appended to the namespace of the calling
        module.

        Args:
            prefix (str):  Text string to append to start of ``test_function`` name
                     when naming generated test cases. This allows reuse of
                     a single ``test_function`` with multiple
                     :class:`TestFactories <.TestFactory>` without name clashes.
            postfix (str): Text string to append to end of ``test_function`` name
                     when naming generated test cases. This allows reuse of
                     a single ``test_function`` with multiple
                     :class:`TestFactories <.TestFactory>` without name clashes.
        """

        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])

        d = self.kwargs

        for index, testoptions in enumerate(
            dict(zip(d, v)) for v in product(*d.values())
        ):

            name = "%s%s%s_%03d" % (prefix, self.name, postfix, index + 1)
            doc = "Automatically generated test\n\n"

            # preprocess testoptions to split tuples
            testoptions_split = {}
            for optname, optvalue in testoptions.items():
                if isinstance(optname, str):
                    testoptions_split[optname] = optvalue
                else:
                    # previously checked in add_option; ensure nothing has changed
                    assert len(optname) == len(optvalue)
                    for n, v in zip(optname, optvalue):
                        testoptions_split[n] = v

            for optname, optvalue in testoptions_split.items():
                if callable(optvalue):
                    if not optvalue.__doc__:
                        desc = "No docstring supplied"
                    else:
                        desc = optvalue.__doc__.split("\n")[0]
                    doc += "\t{}: {} ({})\n".format(
                        optname, optvalue.__qualname__, desc
                    )
                else:
                    doc += "\t{}: {}\n".format(optname, repr(optvalue))

            self.log.debug(
                'Adding generated test "%s" to module "%s"' % (name, mod.__name__)
            )
            kwargs = {}
            kwargs.update(self.kwargs_constant)
            kwargs.update(testoptions_split)
            if hasattr(mod, name):
                self.log.error(
                    "Overwriting %s in module %s. "
                    "This causes a previously defined testcase "
                    "not to be run. Consider setting/changing "
                    "name_postfix" % (name, mod)
                )
            setattr(
                mod,
                name,
                _create_test(self.test_function, name, doc, mod, *self.args, **kwargs),
            )


def _trim(docstring: Optional[str]) -> str:
    """Normalizes test docstrings

    Based on https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation.
    """
    if docstring is None or docstring == "":
        return ""
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = math.inf
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < math.inf:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Add one newline back
    trimmed.insert(0, "")
    # Return a single string:
    return "\n  ".join(trimmed)
