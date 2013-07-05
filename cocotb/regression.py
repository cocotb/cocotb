''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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


import simulator

import cocotb
from cocotb.triggers import NullTrigger

import cocotb.ANSI as ANSI
import cocotb.decorators
from xunit_reporter import XUnitReporter

def _my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod


class RegressionManager(object):
    """Encapsulates all regression capability into a single place"""

    def __init__(self, dut, modules, test=None):
        """
        Args:
            modules (list): A list of python module names to run

        Kwargs
        """
        self._queue = []
        self._dut = dut
        self._modules = modules
        self._function = test
        self._running_test = None
        self.log = logging.getLogger("cocotb.regression")

    def initialise(self):

        self.ntests = 0

        # Auto discovery
        for module_name in self._modules:
            module = _my_import(module_name)

            if self._function:

                # Single function specified, don't auto discover
                if not hasattr(module, self._function):
                    raise AttributeError("Test %s doesn't exist in %s" %
                        (self._function, module_name))

                self._queue.append(getattr(module, self._function)(self._dut))
                self.ntests = 1
                break

            for thing in vars(module).values():
                if hasattr(thing, "im_test"):
                    self._queue.append(thing(self._dut))
                    self.ntests += 1
                    self.log.info("Found test %s.%s" %
                        (self._queue[-1]._func.__module__,
                        self._queue[-1]._func.__name__))


        self.xunit = XUnitReporter()
        self.xunit.add_testsuite(name="all", tests=repr(self.ntests), package="all")       

    def tear_down(self):
        """It's the end of the world as we know it"""
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

        self.xunit.add_testcase(name = self._running_test._func.__name__, 
                                classname=self._running_test._func.__module__,
                                time=repr(time.time() - self._running_test.start_time))
        if isinstance(result, cocotb.decorators.TestCompleteFail):
            self.xunit.add_failure("\n".join(self._running_test.error_messages))

    def execute(self):
        cocotb.scheduler.add(self.test_runner())

    @cocotb.decorators.coroutine
    def test_runner(self):
        self._running_test = cocotb.regression.next_test()
        count = 1
        while self._running_test:
            try:
                # Want this to stand out a little bit
                self.log.info("%sRunning test %d/%d:%s %s" % (
                    ANSI.BLUE_BG +ANSI.BLACK_FG,
                        count, self.ntests,
                    ANSI.DEFAULT_FG + ANSI.DEFAULT_BG,
                        self._running_test))
                if count is 1:
                    test = cocotb.scheduler.add(self._running_test)
                else:
                    test = cocotb.scheduler.new_test(self._running_test)
                yield NullTrigger()
            except StopIteration:
               count+=1
               self._running_test = cocotb.regression.next_test()

        self.tear_down()       
        return 
