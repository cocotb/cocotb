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
Cocotb is a coroutine, cosimulation framework for writing testbenches in Python.

See http://cocotb.readthedocs.org for full documentation
"""
import os
import sys
import logging
import threading
from functools import wraps


import cocotb.handle
from cocotb.scheduler import Scheduler
from cocotb.log import SimLogFormatter
from cocotb.regression import xunit_header

# Things we want in the cocotb namespace
from cocotb.decorators import test, coroutine

# Singleton scheduler instance
# NB this cheekily ensures a singleton since we're replacing the reference
# so that cocotb.scheduler gives you the singleton instance and not the
# scheduler package
scheduler = Scheduler()

# To save typing provide an alias to scheduler.add
fork = scheduler.add

# Top level logger object
log = logging.getLogger('cocotb')
log.setLevel(logging.INFO)

# Add our default log handler
hdlr = logging.StreamHandler(sys.stdout)
hdlr.setFormatter(SimLogFormatter())
log.addHandler(hdlr)


class TestFailed(Exception):
    pass



# FIXME is this really required?
_rlock = threading.RLock()


def _initialise_testbench(root_handle):
    """
    This function is called after the simulator has elaborated all
    entities and is ready to run the test.

    The test must be defined by the environment variables
        MODULE
        FUNCTION

    """
    _rlock.acquire()

    def my_import(name):
        mod = __import__(name)
        components = name.split('.')
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod

    # Create the base handle type
    dut = cocotb.handle.SimHandle(root_handle)
    module_str = os.getenv('MODULE')
    function_str = os.getenv('FUNCTION')

    if not module_str or not function_str:
        raise ImportError("Environment variables with test information not provided.  MODULE=\"%s\" and FUNCTION=\"%s\"" % (module_str, function_str))

    with open("results.xml", 'w') as f:
        f.write(xunit_header())

    testmod = my_import(module_str)
    log.info("Starting testcase %s.%s" % (testmod.__name__, function_str))

    coroutine = getattr(testmod, function_str)(dut)
    log.debug("Got %s %s" % (coroutine.__name__, str(coroutine)))

    scheduler.add(coroutine)
    _rlock.release()
    return True

