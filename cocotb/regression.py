''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""
All things relating to regression capabilities
"""

import time
import logging
import inspect
from itertools import product
import sys
import os
# For autodocumentation don't need the extension modules
if "SPHINX_BUILD" in os.environ:
    simulator = None
else:
    import simulator

# Optional support for coverage collection of testbench files
coverage = None
if "COVERAGE" in os.environ:
    try:
        import coverage
    except ImportError as e:
        sys.stderr.write("Coverage collection requested but coverage module not availble\n")
        sys.stderr.write("Import error was: %s\n" % repr(e))

import cocotb
import cocotb.ANSI as ANSI
from cocotb.log import SimLog
from cocotb.result import TestError, TestFailure, TestSuccess, SimFailure
from cocotb.xunit_reporter import XUnitReporter

def _my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


class RegressionManager(object):
    """Encapsulates all regression capability into a single place"""

    def __init__(self, root_name, modules, tests=None):
        """
        Args:
            modules (list): A list of python module names to run

        Kwargs
        """
        self._queue = []
        self._root_name = root_name
        self._dut = None
        self._modules = modules
        self._functions = tests
        self._running_test = None
        self._cov = None
        self.log = SimLog("cocotb.regression")

    def initialise(self):

        self.ntests = 0
        self.count = 1
        self.skipped = 0
        self.failures = 0
        self.xunit = XUnitReporter()
        self.xunit.add_testsuite(name="all", tests=repr(self.ntests), package="all")

        if coverage is not None:
            self.log.info("Enabling coverage collection of Python code")
            self._cov = coverage.coverage(branch=True, omit=["*cocotb*"])
            self._cov.start()

        self._dut = cocotb.handle.SimHandle(simulator.get_root_handle(self._root_name))
        if self._dut is None:
            raise AttributeError("Can not find Root Handle (%s)" % root_name)

        # Auto discovery
        for module_name in self._modules:
            module = _my_import(module_name)

            if self._functions:

                # Specific functions specified, don't auto discover
                for test in self._functions.rsplit(','):
                    if not hasattr(module, test):
                        raise AttributeError("Test %s doesn't exist in %s" %
                            (test, module_name))

                    self._queue.append(getattr(module, test)(self._dut))
                    self.ntests += 1
                break

            for thing in vars(module).values():
                if hasattr(thing, "im_test"):
                    try:
                        test = thing(self._dut)
                        skip = test.skip
                    except TestError:
                        skip = True
                        self.log.warning("Failed to initialise test %s" % thing.name)

                    if skip:
                        self.log.info("Skipping test %s" % thing.name)
                        self.xunit.add_testcase(name=thing.name, classname=module_name, time="0.0")
                        self.xunit.add_skipped()
                        self.skipped += 1                        
                    else:
                        self._queue.append(test)
                        self.ntests += 1

        self._queue.sort(key=lambda test: "%s.%s" % (test.module, test.funcname))

        for valid_tests in self._queue:
            self.log.info("Found test %s.%s" %
                        (valid_tests.module,
                         valid_tests.funcname))

    def tear_down(self):
        """It's the end of the world as we know it"""
        if self.failures:
            self.log.error("Failed %d out of %d tests (%d skipped)" %
                (self.failures, self.count -1, self.skipped))
        else:
            self.log.info("Passed %d tests (%d skipped)"  %
                (self.count-1, self.skipped))
        if self._cov:
            self._cov.stop()
            self.log.info("Writing coverage data")
            self._cov.save()
            self._cov.html_report()
        self.log.info("Shutting down...")
        self.xunit.write()
        simulator.stop_simulator()


    def next_test(self):
        """Get the next test to run"""
        if not self._queue: return None
        return self._queue.pop(0)


    def handle_result(self, result):
        """Handle a test result

        Dumps result to XML and schedules the next test (if any)

        Args: result (TestComplete exception)
        """
        self.xunit.add_testcase(name =self._running_test.funcname,
                                classname=self._running_test.module,
                                time=repr(time.time() - self._running_test.start_time) )

        if isinstance(result, TestSuccess) and not self._running_test.expect_fail and not self._running_test.expect_error:
            self.log.info("Test Passed: %s" % self._running_test.funcname)

        elif isinstance(result, TestFailure) and self._running_test.expect_fail:
            self.log.info("Test failed as expected: %s (result was %s)" % (
                          self._running_test.funcname, result.__class__.__name__))

        elif isinstance(result, TestSuccess) and self._running_test.expect_error:
            self.log.error("Test passed but we expected an error: %s (result was %s)" % (
                           self._running_test.funcname, result.__class__.__name__))
            self.xunit.add_failure(stdout=repr(str(result)), stderr="\n".join(self._running_test.error_messages))
            self.failures += 1

        elif isinstance(result, TestSuccess):
            self.log.error("Test passed but we expected a failure: %s (result was %s)" % (
                           self._running_test.funcname, result.__class__.__name__))
            self.xunit.add_failure(stdout=repr(str(result)), stderr="\n".join(self._running_test.error_messages))
            self.failures += 1

        elif isinstance(result, TestError) and self._running_test.expect_error:
            self.log.info("Test errored as expected: %s (result was %s)" % (
                          self._running_test.funcname, result.__class__.__name__))

        elif isinstance(result, SimFailure):
            if self._running_test.expect_error:
                self.log.info("Test errored as expected: %s (result was %s)" % (
                              self._running_test.funcname, result.__class__.__name__))
            else:
                self.log.error("Test error has lead to simulator shuttting us down")
                self.failures += 1
                self.tear_down()
                return

        else:
            self.log.error("Test Failed: %s (result was %s)" % (
                        self._running_test.funcname, result.__class__.__name__))
            self.xunit.add_failure(stdout=repr(str(result)), stderr="\n".join(self._running_test.error_messages))
            self.failures += 1

        self.execute()

    def execute(self):
        self._running_test = cocotb.regression.next_test()
        if self._running_test:
            # Want this to stand out a little bit
            self.log.info("%sRunning test %d/%d:%s %s" % (
               ANSI.BLUE_BG +ANSI.BLACK_FG,
                    self.count, self.ntests,
               ANSI.DEFAULT_FG + ANSI.DEFAULT_BG,
                    self._running_test.funcname))
            if self.count is 1:
                test = cocotb.scheduler.add(self._running_test)
            else:
                test = cocotb.scheduler.new_test(self._running_test)
            self.count+=1
        else:
            self.tear_down()


def _create_test(function, name, documentation, mod, *args, **kwargs):
    """Factory function to create tests, avoids late binding

    Creates a test dynamically.  The test will call the supplied
    function with the supplied arguments.

    Args:
        function: (function)    the test function to run

        name: (string)          the name of the test

        documentation: (string) the docstring for the test

        mod: (module)           the module this function belongs to

        *args:                  remaining args to pass to test function

    Kwaygs:
        **kwargs:               passed to the test function

    Returns:
        decorated test function
    """
    def _my_test(dut):
        yield function(dut, *args, **kwargs)

    _my_test.__name__ = name
    _my_test.__doc__ = documentation
    _my_test.__module__ = mod.__name__
    return cocotb.test()(_my_test)


class TestFactory(object):

    """
    Used to automatically generate tests.

    Assuming we have a common test function that will run a test. This test
    function will take keyword arguments (for example generators for each of
    the input interfaces) and generate tests that call the supplied function.

    This Factory allows us to generate sets of tests based on the different
    permutations of the possible arguments to the test function.

    For example if we have a module that takes backpressure and idles and
    have some packet generations routines gen_a and gen_b.

    >>> tf = TestFactory(run_test)
    >>> tf.add_option('data_in', [gen_a, gen_b])
    >>> tf.add_option('backpressure', [None, random_backpressure])
    >>> tf.add_option('idles', [None, random_idles])
    >>> tf.generate_tests()

    We would get the following tests:
        * gen_a with no backpressure and no idles
        * gen_a with no backpressure and random_idles
        * gen_a with random_backpressure and no idles
        * gen_a with random_backpressure and random_idles
        * gen_b with no backpressure and no idles
        * gen_b with no backpressure and random_idles
        * gen_b with random_backpressure and no idles
        * gen_b with random_backpressure and random_idles

    The tests are appended to the calling module for auto-discovery.

    Tests are simply named test_function_N. The docstring for the test (hence
    the test description) includes the name and description of each generator.
    """

    def __init__(self, test_function, *args, **kwargs):
        """
        Args:
            test_function (function): the function that executes a test.
                                      Must take 'dut' as the first argument.

            *args: Remaining args are passed directly to the test function.
                   Note that these arguments are not varied. An argument that
                   varies with each test must be a keyword argument to the
                   test function.
            *kwargs: Remaining kwargs are passed directly to the test function.
                   Note that these arguments are not varied. An argument that
                   varies with each test must be a keyword argument to the
                   test function.
        """
        if not isinstance(test_function, cocotb.coroutine):
            raise TypeError("TestFactory requires a cocotb coroutine")
        self.test_function = test_function
        self.name = self.test_function._func.__name__

        self.args = args
        self.kwargs_constant = kwargs
        self.kwargs = {}

    def add_option(self, name, optionlist):
        """Add a named option to the test.

        Args:
           name (string): name of the option. passed to test as a keyword
                          argument

           optionlist (list): A list of possible options for this test knob
        """
        self.kwargs[name] = optionlist

    def generate_tests(self, prefix="", postfix=""):
        """
        Generates exhasutive set of tests using the cartesian product of the
        possible keyword arguments.

        The generated tests are appended to the namespace of the calling 
        module.

        Args:
            prefix:  Text string to append to start of test_function name
                     when naming generated test cases. This allows reuse of
                     a single test_function with multiple TestFactories without
                     name clashes.
            postfix: Text string to append to end of test_function name
                     when naming generated test cases. This allows reuse of
                     a single test_function with multiple TestFactories without
                     name clashes.
        """

        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])

        d = self.kwargs

        for index, testoptions in enumerate( (dict(zip(d, v)) for v in product(*d.values())) ):

            name = "%s%s%s_%03d" % (prefix, self.name, postfix, index + 1)
            doc = "Automatically generated test\n\n"

            for optname, optvalue in testoptions.items():
                if callable(optvalue):
                    if not optvalue.__doc__: desc = "No docstring supplied"
                    else: desc = optvalue.__doc__.split('\n')[0]
                    doc += "\t%s: %s (%s)\n" % (optname, optvalue.__name__, desc)
                else:
                    doc += "\t%s: %s\n" % (optname, repr(optvalue))

            cocotb.log.debug("Adding generated test \"%s\" to module \"%s\"" % (name, mod.__name__))
            kwargs = {}
            kwargs.update(self.kwargs_constant)
            kwargs.update(testoptions)
            if hasattr(mod, name):
                cocotb.log.error("Overwriting %s in module %s. This causes previously defined testcase "
                                 "not to be run. Consider setting/changing name_postfix" % (name, mod))
            setattr(mod, name, _create_test(self.test_function, name, doc, mod, *self.args, **kwargs))

