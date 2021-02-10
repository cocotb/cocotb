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

import time
import inspect
from itertools import product
import sys
import os
import traceback
import pdb
from typing import Any, Optional, Tuple, Iterable

import cocotb
import cocotb.ANSI as ANSI
from cocotb.log import SimLog
from cocotb.result import TestSuccess, SimFailure
from cocotb.utils import get_sim_time, remove_traceback_frames, want_color_output
from cocotb.xunit_reporter import XUnitReporter
from cocotb.decorators import test as Test, hook as Hook, RunningTask
from cocotb.outcomes import Outcome, Error
from cocotb.handle import SimHandle

from cocotb import simulator

_pdb_on_exception = "COCOTB_PDB_ON_EXCEPTION" in os.environ

# Optional support for coverage collection of testbench files
coverage = None
if "COVERAGE" in os.environ:
    try:
        import coverage
    except ImportError as e:
        msg = ("Coverage collection requested but coverage module not available"
               "\n"
               "Import error was: %s\n" % repr(e))
        sys.stderr.write(msg)


def _my_import(name: str) -> Any:
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


_logger = SimLog(__name__)


class RegressionManager:
    """Encapsulates all regression capability into a single place"""

    def __init__(self, dut: SimHandle, tests: Iterable[Test], hooks: Iterable[Hook]):
        """
        Args:
            dut (SimHandle): The root handle to pass into test functions.
            tests (Iterable[Test]): tests to run
            hooks (Iterable[Hook]): hooks to tun
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
        self.skipped = 0
        self.failures = 0
        self._tearing_down = False

        # Setup XUnit
        ###################

        results_filename = os.getenv('COCOTB_RESULTS_FILE', "results.xml")
        suite_name = os.getenv('RESULT_TESTSUITE', "all")
        package_name = os.getenv('RESULT_TESTPACKAGE', "all")

        self.xunit = XUnitReporter(filename=results_filename)

        self.xunit.add_testsuite(name=suite_name, package=package_name)

        self.xunit.add_property(name="random_seed", value=str(cocotb.RANDOM_SEED))

        # Setup Coverage
        ####################

        if coverage is not None:
            self.log.info("Enabling coverage collection of Python code")
            # Exclude cocotb itself from coverage collection.
            cocotb_package_dir = os.path.dirname(__file__)
            self._cov = coverage.coverage(branch=True, omit=["{}/*".format(cocotb_package_dir)])
            self._cov.start()

        # Test Discovery
        ####################
        self._queue = []
        for test in tests:
            self.log.info("Found test {}.{}".format(test.__module__, test.__qualname__))
            self._queue.append(test)
        self.ntests = len(self._queue)

        if not self._queue:
            self.log.warning("No tests were discovered")

        self._queue.sort(key=lambda test: (test.stage, test._id))

        # Process Hooks
        ###################
        for hook in hooks:
            self.log.info("Found hook {}.{}".format(hook.__module__, hook.__qualname__))
            self._init_hook(hook)

    @classmethod
    def from_discovery(cls, dut: SimHandle):
        """
        Obtains the test and hook lists by discovery.

        See :envvar:`MODULE` and :envvar:`TESTCASE` for details on how tests are discovered.

        Args:
            dut (SimHandle): The root handle to pass into test functions.
        """
        tests = cls._discover_tests()
        hooks = cls._discover_hooks()
        return cls(dut, tests, hooks)

    @staticmethod
    def _discover_tests() -> Iterable[Test]:
        """
        Discovers tests in files automatically.

        See :envvar:`MODULE` and :envvar:`TESTCASE` for details on how tests are discovered.
        """
        module_str = os.getenv('MODULE')
        test_str = os.getenv('TESTCASE')

        if module_str is None:
            raise ValueError("Environment variable MODULE, which defines the module(s) to execute, is not defined.")

        modules = [s.strip() for s in module_str.split(',') if s.strip()]

        for module_name in modules:
            try:
                _logger.debug("Python Path: " + ",".join(sys.path))
                _logger.debug("PWD: " + os.getcwd())
                module = _my_import(module_name)
            except Exception as E:
                _logger.critical("Failed to import module %s: %s", module_name, E)
                _logger.info("MODULE variable was \"%s\"", ".".join(modules))
                _logger.info("Traceback: ")
                _logger.info(traceback.format_exc())
                raise

            if test_str:

                # Specific functions specified, don't auto-discover
                for test_name in test_str.rsplit(','):
                    try:
                        test = getattr(module, test_name)
                    except AttributeError:
                        _logger.error("Requested test %s wasn't found in module %s", test_name, module_name)
                        err = AttributeError("Test %s doesn't exist in %s" % (test_name, module_name))
                        raise err from None  # discard nested traceback

                    if not isinstance(test, Test):
                        _logger.error("Requested %s from module %s isn't a cocotb.test decorated coroutine",
                                      test_name, module_name)
                        raise ImportError("Failed to find requested test %s" % test_name)

                    # If we request a test manually, it should be run even if skip=True is set.
                    test.skip = False

                    yield test

                # only look in first module for all functions and don't complain if all functions are not found
                break

            # auto-discover
            for thing in vars(module).values():
                if isinstance(thing, Test):
                    yield thing

    @staticmethod
    def _discover_hooks() -> Iterable[Hook]:
        """
        Discovers hooks automatically.

        See :envvar:`COCOTB_HOOKS` for details on how hooks are discovered.
        """
        hooks_str = os.getenv('COCOTB_HOOKS', '')
        hooks = [s.strip() for s in hooks_str.split(',') if s.strip()]

        for module_name in hooks:
            _logger.info("Loading hook from module '" + module_name + "'")
            module = _my_import(module_name)

            for thing in vars(module).values():
                if hasattr(thing, "im_hook"):
                    yield thing

    def _init_hook(self, hook: Hook) -> Optional[RunningTask]:
        try:
            test = hook(self._dut)
        except Exception:
            self.log.warning("Failed to initialize hook %s" % hook.name, exc_info=True)
        else:
            return cocotb.scheduler.add(test)

    def tear_down(self) -> None:
        # prevent re-entering the tear down procedure
        if not self._tearing_down:
            self._tearing_down = True
        else:
            return

        # fail remaining tests
        while True:
            test = self.next_test()
            if test is None:
                break
            self._record_result(
                test=test,
                outcome=Error(SimFailure),
                wall_time_s=0,
                sim_time_ns=0)

        # Write out final log messages
        self._log_test_summary()
        self._log_sim_summary()
        self.log.info("Shutting down...")

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

    def next_test(self) -> Optional[Test]:
        """Get the next test to run"""
        if not self._queue:
            return None
        self.count += 1
        return self._queue.pop(0)

    def handle_result(self, test: RunningTask) -> None:
        """Handle a test completing.

        Dump result to XML and schedule the next test (if any). Entered by the scheduler.

        Args:
            test: The test that completed
        """
        assert test is self._test_task

        real_time = time.time() - self._test_start_time
        sim_time_ns = get_sim_time('ns') - self._test_start_sim_time

        # stop capturing log output
        cocotb.log.removeHandler(test.handler)

        self._record_result(
            test=self._test,
            outcome=self._test_task._outcome,
            wall_time_s=real_time,
            sim_time_ns=sim_time_ns)

        self.execute()

    def _init_test(self, test: Test) -> Optional[RunningTask]:
        """Initialize a test.

        Record outcome if the initialization fails.
        Record skip if the test is skipped.
        Save the initialized test if it successfully initializes.
        """

        if test.skip:
            hilight_start = ANSI.COLOR_TEST if want_color_output() else ''
            hilight_end = ANSI.COLOR_DEFAULT if want_color_output() else ''
            # Want this to stand out a little bit
            self.log.info("{}Skipping test {}/{}:{} {}".format(
                hilight_start,
                self.count,
                self.ntests,
                hilight_end,
                test.__qualname__))
            self._record_result(test, None, 0, 0)
            return None

        test_init_outcome = cocotb.outcomes.capture(test, self._dut)

        if isinstance(test_init_outcome, cocotb.outcomes.Error):
            self.log.error("Failed to initialize test %s" % test.__qualname__,
                           exc_info=test_init_outcome.error)
            self._record_result(test, test_init_outcome, 0, 0)
            return None

        test = test_init_outcome.get()
        return test

    def _score_test(self, test: Test, outcome: Outcome) -> Tuple[bool, bool]:
        """
        Given a test and the test's outcome, determine if the test met expectations and log pertinent information
        """

        # Helper for logging result
        def _result_was():
            result_was = ("{} (result was {})".format
                          (test.__qualname__, type(result).__qualname__))
            return result_was

        # scoring outcomes
        result_pass = True
        sim_failed = False

        try:
            outcome.get()
        except Exception as e:
            result = remove_traceback_frames(e, ['_score_test', 'get'])
        else:
            result = TestSuccess()

        if (isinstance(result, TestSuccess) and
                not test.expect_fail and
                not test.expect_error):
            self.log.info("Test Passed: %s" % test.__qualname__)

        elif (isinstance(result, AssertionError) and
                test.expect_fail):
            self.log.info("Test failed as expected: " + _result_was())

        elif (isinstance(result, TestSuccess) and
              test.expect_error):
            self.log.error("Test passed but we expected an error: " +
                           _result_was())
            result_pass = False

        elif isinstance(result, TestSuccess):
            self.log.error("Test passed but we expected a failure: " +
                           _result_was())
            result_pass = False

        elif isinstance(result, SimFailure):
            if isinstance(result, test.expect_error):
                self.log.info("Test errored as expected: " + _result_was())
            else:
                self.log.error("Test error has lead to simulator shutting us "
                               "down", exc_info=result)
                result_pass = False
            # whether we expected it or not, the simulation has failed unrecoverably
            sim_failed = True

        elif test.expect_error:
            if isinstance(result, test.expect_error):
                self.log.info("Test errored as expected: " + _result_was())
            else:
                self.log.error("Test errored with unexpected type: " + _result_was(), exc_info=result)
                result_pass = False

        else:
            self.log.error("Test Failed: " + _result_was(), exc_info=result)
            result_pass = False

            if _pdb_on_exception:
                pdb.post_mortem(result.__traceback__)

        return result_pass, sim_failed

    def _record_result(
        self,
        test: Test,
        outcome: Optional[Outcome],
        wall_time_s: float,
        sim_time_ns: float
    ) -> None:

        ratio_time = self._safe_divide(sim_time_ns, wall_time_s)
        try:
            lineno = inspect.getsourcelines(test._func)[1]
        except OSError:
            lineno = 1

        self.xunit.add_testcase(name=test.__qualname__,
                                classname=test.__module__,
                                file=inspect.getfile(test._func),
                                lineno=repr(lineno),
                                time=repr(wall_time_s),
                                sim_time_ns=repr(sim_time_ns),
                                ratio_time=repr(ratio_time))

        if outcome is None:  # skipped
            test_pass, sim_failed = None, False
            self.xunit.add_skipped()
            self.skipped += 1

        else:
            test_pass, sim_failed = self._score_test(test, outcome)
            if not test_pass:
                self.xunit.add_failure()
                self.failures += 1

        self.test_results.append({
            'test': '.'.join([test.__module__, test.__qualname__]),
            'pass': test_pass,
            'sim': sim_time_ns,
            'real': wall_time_s,
            'ratio': ratio_time})

        if sim_failed:
            self.tear_down()
            return

    def execute(self) -> None:
        while True:
            self._test = self.next_test()
            if self._test is None:
                return self.tear_down()

            self._test_task = self._init_test(self._test)
            if self._test_task is not None:
                return self._start_test()

    def _start_test(self) -> None:
        start = ''
        end = ''
        if want_color_output():
            start = ANSI.COLOR_TEST
            end = ANSI.COLOR_DEFAULT
        # Want this to stand out a little bit
        self.log.info("%sRunning test %d/%d:%s %s" %
                      (start,
                       self.count, self.ntests,
                       end,
                       self._test.__qualname__))

        # start capturing log output
        cocotb.log.addHandler(self._test_task.handler)

        self._test_start_time = time.time()
        self._test_start_sim_time = get_sim_time('ns')
        cocotb.scheduler._add_test(self._test_task)

    def _log_test_summary(self) -> None:

        if self.failures:
            self.log.error("Failed %d out of %d tests (%d skipped)" %
                           (self.failures, self.count, self.skipped))
        else:
            self.log.info("Passed %d tests (%d skipped)" %
                          (self.count, self.skipped))

        if len(self.test_results) == 0:
            return

        TEST_FIELD = 'TEST'
        RESULT_FIELD = 'PASS/FAIL'
        SIM_FIELD = 'SIM TIME(NS)'
        REAL_FIELD = 'REAL TIME(S)'
        RATIO_FIELD = 'RATIO(NS/S)'

        TEST_FIELD_LEN = max(len(TEST_FIELD), len(max([x['test'] for x in self.test_results], key=len)))
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
            e_len=RATIO_FIELD_LEN)

        LINE_LEN = 3 + TEST_FIELD_LEN + 2 + RESULT_FIELD_LEN + 2 + SIM_FIELD_LEN + 2 + \
            REAL_FIELD_LEN + 2 + RATIO_FIELD_LEN + 3

        LINE_SEP = "*" * LINE_LEN + "\n"

        summary = ""
        summary += LINE_SEP
        summary += "** {a:<{a_len}}  {b:^{b_len}}  {c:>{c_len}}  {d:>{d_len}}  {e:>{e_len}} **\n".format(**header_dict)
        summary += LINE_SEP

        test_line = "{start}** {a:<{a_len}}  {b:^{b_len}}  {c:>{c_len}.2f}   {d:>{d_len}.2f}   {e:>{e_len}.2f}  **\n"
        for result in self.test_results:
            hilite = ''

            if result['pass'] is None:
                pass_fail_str = "N/A"
            elif result['pass']:
                pass_fail_str = "PASS"
            else:
                pass_fail_str = "FAIL"
                if want_color_output():
                    hilite = ANSI.COLOR_HILITE_SUMMARY

            test_dict = dict(
                a=result['test'],
                b=pass_fail_str,
                c=result['sim'],
                d=result['real'],
                e=result['ratio'],
                a_len=TEST_FIELD_LEN,
                b_len=RESULT_FIELD_LEN,
                c_len=SIM_FIELD_LEN - 1,
                d_len=REAL_FIELD_LEN - 1,
                e_len=RATIO_FIELD_LEN - 1,
                start=hilite)

            summary += test_line.format(**test_dict)

        summary += LINE_SEP

        self.log.info(summary)

    def _log_sim_summary(self) -> None:
        real_time = time.time() - self.start_time
        sim_time_ns = get_sim_time('ns')
        ratio_time = self._safe_divide(sim_time_ns, real_time)

        summary = ""

        summary += "*************************************************************************************\n"
        summary += "**                                 ERRORS : {0:<39}**\n".format(self.failures)
        summary += "*************************************************************************************\n"
        summary += "**                               SIM TIME : {0:<39}**\n".format('{0:.2f} NS'.format(sim_time_ns))
        summary += "**                              REAL TIME : {0:<39}**\n".format('{0:.2f} S'.format(real_time))
        summary += "**                        SIM / REAL TIME : {0:<39}**\n".format('{0:.2f} NS/S'.format(ratio_time))
        summary += "*************************************************************************************\n"

        self.log.info(summary)

    @staticmethod
    def _safe_divide(a: float, b: float) -> float:
        try:
            return a / b
        except ZeroDivisionError:
            if a == 0:
                return float('nan')
            else:
                return float('inf')


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
        test_function: The function that executes a test.
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
        if sys.version_info > (3, 6) and inspect.isasyncgenfunction(test_function):
            raise TypeError("Expected a coroutine function, but got the async generator '{}'. "
                            "Did you forget to convert a `yield` to an `await`?"
                            .format(test_function.__qualname__))
        if not (isinstance(test_function, cocotb.coroutine) or inspect.iscoroutinefunction(test_function)):
            raise TypeError("TestFactory requires a cocotb coroutine")
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
                    raise ValueError("Mismatch between number of options and number of option values in group")
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

        for index, testoptions in enumerate((
                                            dict(zip(d, v)) for v in
                                            product(*d.values())
                                            )):

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
                        desc = optvalue.__doc__.split('\n')[0]
                    doc += "\t%s: %s (%s)\n" % (optname, optvalue.__qualname__,
                                                desc)
                else:
                    doc += "\t%s: %s\n" % (optname, repr(optvalue))

            self.log.debug("Adding generated test \"%s\" to module \"%s\"" %
                           (name, mod.__name__))
            kwargs = {}
            kwargs.update(self.kwargs_constant)
            kwargs.update(testoptions_split)
            if hasattr(mod, name):
                self.log.error("Overwriting %s in module %s. "
                               "This causes a previously defined testcase "
                               "not to be run. Consider setting/changing "
                               "name_postfix" % (name, mod))
            setattr(mod, name, _create_test(self.test_function, name, doc, mod,
                                            *self.args, **kwargs))
