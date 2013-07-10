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
from cocotb.regression import RegressionManager

# Things we want in the cocotb namespace
from cocotb.decorators import test, coroutine

# Singleton scheduler instance
# NB this cheekily ensures a singleton since we're replacing the reference
# so that cocotb.scheduler gives you the singleton instance and not the
# scheduler package
scheduler = Scheduler()
regression = None

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
        TESTCASE
    """
    _rlock.acquire()

    # Create the base handle type
    dut = cocotb.handle.SimHandle(root_handle)
    module_str = os.getenv('MODULE')
    test_str = os.getenv('TESTCASE')

    if not module_str:
        raise ImportError("Environment variables defining the module(s) to \
                        execute not defined.  MODULE=\"%s\"\"" % (module_str))

    modules = module_str.split(',')

    global regression

    regression = RegressionManager(dut, modules, tests=test_str)
    regression.initialise()
    regression.execute()

    _rlock.release()
    return True

