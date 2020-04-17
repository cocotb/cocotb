# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.

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

"""
Cocotb is a coroutine, cosimulation framework for writing testbenches in Python.

See https://docs.cocotb.org for full documentation
"""
import os
import sys
import logging
import threading
import random
import time
import warnings

import cocotb.handle
import cocotb.log
from cocotb.scheduler import Scheduler
from cocotb.regression import RegressionManager


# Things we want in the cocotb namespace
from cocotb.decorators import test, coroutine, hook, function, external  # noqa: F401

# Singleton scheduler instance
# NB this cheekily ensures a singleton since we're replacing the reference
# so that cocotb.scheduler gives you the singleton instance and not the
# scheduler package

from ._version import __version__

# GPI logging instance
if "COCOTB_SIM" in os.environ:

    # sys.path normally includes "" (the current directory), but does not appear to when python is embedded.
    # Add it back because users expect to be able to import files in their test directory.
    # TODO: move this to gpi_embed.cpp
    sys.path.insert(0, "")

    def _reopen_stream_with_buffering(stream_name):
        try:
            if not getattr(sys, stream_name).isatty():
                setattr(sys, stream_name, os.fdopen(getattr(sys, stream_name).fileno(), 'w', 1))
                return True
            return False
        except Exception as e:
            return e

    # If stdout/stderr are not TTYs, Python may not have opened them with line
    # buffering. In that case, try to reopen them with line buffering
    # explicitly enabled. This ensures that prints such as stack traces always
    # appear. Continue silently if this fails.
    _stdout_buffer_result = _reopen_stream_with_buffering('stdout')
    _stderr_buffer_result = _reopen_stream_with_buffering('stderr')

    # Don't set the logging up until we've attempted to fix the standard IO,
    # otherwise it will end up connected to the unfixed IO.
    cocotb.log.default_config()
    log = logging.getLogger(__name__)

    # we can't log these things until the logging is set up!
    if _stderr_buffer_result is True:
        log.debug("Reopened stderr with line buffering")
    if _stdout_buffer_result is True:
        log.debug("Reopened stdout with line buffering")
    if isinstance(_stdout_buffer_result, Exception) or isinstance(_stderr_buffer_result, Exception):
        if isinstance(_stdout_buffer_result, Exception):
            log.warning("Failed to ensure that stdout is line buffered", exc_info=_stdout_buffer_result)
        if isinstance(_stderr_buffer_result, Exception):
            log.warning("Failed to ensure that stderr is line buffered", exc_info=_stderr_buffer_result)
        log.warning("Some stack traces may not appear because of this.")

    del _stderr_buffer_result, _stdout_buffer_result

    # From https://www.python.org/dev/peps/pep-0565/#recommended-filter-settings-for-test-runners
    # If the user doesn't want to see these, they can always change the global
    # warning settings in their test module.
    if not sys.warnoptions:
        warnings.simplefilter("default")

scheduler = Scheduler()
"""The global scheduler instance."""

regression_manager = None

plusargs = {}
"""A dictionary of "plusargs" handed to the simulation."""

# To save typing provide an alias to scheduler.add
fork = scheduler.add

# FIXME is this really required?
_rlock = threading.RLock()


def mem_debug(port):
    import cocotb.memdebug
    cocotb.memdebug.start(port)


def _initialise_testbench(root_name):
    """Initialize testbench.

    This function is called after the simulator has elaborated all
    entities and is ready to run the test.

    The test must be defined by the environment variables
    :envvar:`MODULE` and :envvar:`TESTCASE`.

    The environment variable :envvar:`COCOTB_HOOKS`, if present, contains a
    comma-separated list of modules to be executed before the first test.
    """
    _rlock.acquire()

    memcheck_port = os.getenv('MEMCHECK')
    if memcheck_port is not None:
        mem_debug(int(memcheck_port))

    log.info("Running tests with cocotb v%s from %s" %
             (__version__, os.path.dirname(__file__)))

    # Create the base handle type

    process_plusargs()

    # Seed the Python random number generator to make this repeatable
    global RANDOM_SEED
    RANDOM_SEED = os.getenv('RANDOM_SEED')

    if RANDOM_SEED is None:
        if 'ntb_random_seed' in plusargs:
            RANDOM_SEED = eval(plusargs['ntb_random_seed'])
        elif 'seed' in plusargs:
            RANDOM_SEED = eval(plusargs['seed'])
        else:
            RANDOM_SEED = int(time.time())
        log.info("Seeding Python random module with %d" % (RANDOM_SEED))
    else:
        RANDOM_SEED = int(RANDOM_SEED)
        log.info("Seeding Python random module with supplied seed %d" % (RANDOM_SEED))
    random.seed(RANDOM_SEED)

    module_str = os.getenv('MODULE')
    test_str = os.getenv('TESTCASE')
    hooks_str = os.getenv('COCOTB_HOOKS', '')

    if module_str is None:
        raise ValueError("Environment variable MODULE, which defines the module(s) to execute, is not defined.")

    modules = [s.strip() for s in module_str.split(',') if s.strip()]
    hooks = [s.strip() for s in hooks_str.split(',') if s.strip()]

    global regression_manager

    regression_manager = RegressionManager(root_name, modules, tests=test_str, seed=RANDOM_SEED, hooks=hooks)
    regression_manager.initialise()
    regression_manager.execute()

    _rlock.release()
    return True


def _sim_event(level, message):
    """Function that can be called externally to signal an event."""
    SIM_INFO = 0
    SIM_TEST_FAIL = 1
    SIM_FAIL = 2
    from cocotb.result import TestFailure, SimFailure

    if level is SIM_TEST_FAIL:
        scheduler.log.error("Failing test at simulator request")
        scheduler.finish_test(TestFailure("Failure from external source: %s" %
                              message))
    elif level is SIM_FAIL:
        # We simply return here as the simulator will exit
        # so no cleanup is needed
        msg = ("Failing test at simulator request before test run completion: "
               "%s" % message)
        scheduler.log.error(msg)
        scheduler.finish_scheduler(SimFailure(msg))
    else:
        scheduler.log.error("Unsupported sim event")

    return True


def process_plusargs():

    global plusargs

    plusargs = {}

    for option in cocotb.argv:
        if option.startswith('+'):
            if option.find('=') != -1:
                (name, value) = option[1:].split('=')
                plusargs[name] = value
            else:
                plusargs[option[1:]] = True
