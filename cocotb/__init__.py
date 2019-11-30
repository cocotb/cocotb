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

See http://cocotb.readthedocs.org for full documentation
"""
import os
import sys
import logging
import threading
import random
import time

import cocotb.handle
from cocotb.scheduler import Scheduler
from cocotb.log import SimBaseLog, SimLog
from cocotb.regression import RegressionManager


# Things we want in the cocotb namespace
from cocotb.decorators import test, coroutine, hook, function, external  # noqa: F401
from cocotb.decorators import bfm, bfm_import, bfm_export
from cocotb.decorators import bfm_vlog, bfm_sv
from cocotb.decorators import bfm_uint8_t, bfm_int8_t, bfm_uint16_t, bfm_int16_t
from cocotb.decorators import bfm_uint32_t, bfm_int32_t, bfm_uint64_t, bfm_int64_t
from cocotb.bfms import bfm_hdl_path, BfmMgr

# Singleton scheduler instance
# NB this cheekily ensures a singleton since we're replacing the reference
# so that cocotb.scheduler gives you the singleton instance and not the
# scheduler package

from ._version import __version__

# GPI logging instance
if "COCOTB_SIM" in os.environ:
    import simulator
    logging.basicConfig()
    logging.setLoggerClass(SimBaseLog)
    log = SimLog('cocotb')
    level = os.getenv("COCOTB_LOG_LEVEL", "INFO")
    try:
        _default_log = getattr(logging, level)
    except AttributeError as e:
        log.error("Unable to set loging level to %s" % level)
        _default_log = logging.INFO
    log.setLevel(_default_log)
    loggpi = SimLog('cocotb.gpi')
    # Notify GPI of log level
    simulator.log_level(_default_log)

    # If stdout/stderr are not TTYs, Python may not have opened them with line
    # buffering. In that case, try to reopen them with line buffering
    # explicitly enabled. This ensures that prints such as stack traces always
    # appear. Continue silently if this fails.
    try:
        if not sys.stdout.isatty():
            sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
            log.debug("Reopened stdout with line buffering")
        if not sys.stderr.isatty():
            sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)
            log.debug("Reopened stderr with line buffering")
    except Exception as e:
        log.warning("Failed to ensure that stdout/stderr are line buffered: %s", e)
        log.warning("Some stack traces may not appear because of this.")


scheduler = Scheduler()
"""The global scheduler instance."""

regression_manager = None

plusargs = {}

# To save typing provide an alias to scheduler.add
fork = scheduler.add

# FIXME is this really required?
_rlock = threading.RLock()


def mem_debug(port):
    import cocotb.memdebug
    cocotb.memdebug.start(port)


def _initialise_testbench(root_name):
    """
    This function is called after the simulator has elaborated all
    entities and is ready to run the test.

    The test must be defined by the environment variables
        MODULE
        TESTCASE

    The environment variable COCOTB_HOOKS contains a comma-separated list of
        modules that should be executed before the first test.
    """
    _rlock.acquire()
    
    # Initialize plusargs first so we can reference them
    # for initialization
    process_plusargs()

    memcheck_port = get_option('MEMCHECK', 'cocotb.memcheck')
    if memcheck_port is not None:
        mem_debug(int(memcheck_port))

    exec_path = os.getenv('COCOTB_PY_DIR')
    if exec_path is None:
        exec_path = 'Unknown'

    log.info("Running tests with cocotb v%s from %s" %
             (__version__, exec_path))

    # Create the base handle type


    # Seed the Python random number generator to make this repeatable
    global RANDOM_SEED
    RANDOM_SEED = os.getenv('RANDOM_SEED')

    if RANDOM_SEED is None:
        if 'cocotb.seed' in plusargs:
            RANDOM_SEED = eval(plusargs['cocotb.seed'])
        elif 'ntb_random_seed' in plusargs:
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

    modules = get_option('MODULE', 'cocotb.module', is_list=True)
    test_str = get_option('TESTCASE', 'cocotb.testcase')
    hooks = get_option('COCOTB_HOOKS', 'cocotb.hooks', [], is_list=True)
    
    module_path = get_option('COCOTB_PYPATH', 'cocotb.pypath', is_list=True)
    
    if module_path is not None:
        seen = {}
        for p in module_path:
            if p not in seen:
                sys.path.append(p)
                seen[p] = 1

    if modules is None or len(modules) == 0:
        raise ImportError("Environment variables defining the module(s) to " +
                          "execute not defined.  MODULE=\"%s\"" % (modules))

    # Initialize BFMs
    BfmMgr.init()

    global regression_manager

    regression_manager = RegressionManager(root_name, modules, tests=test_str, seed=RANDOM_SEED, hooks=hooks)
    regression_manager.initialise()
    regression_manager.execute()

    _rlock.release()
    return True

def get_option(env_var, plusarg, default=None, is_list=False):
    '''
    Check for an option, looking first in an environment variable,
    next in a plusarg, and finally applying a default
    '''
    
    is_plusarg = False
    
    val = os.getenv(env_var)
    
    if val is None and plusarg in plusargs.keys():
        val = plusargs[plusarg]
        is_plusarg = True
        
    if val is None:
        val = default
        
    if is_list and val is not None:
        # Convert to a list if it isn't already
        if is_plusarg:
            if not isinstance(val, list):
                val = [val]
        else:
            # We split environment-variable values to form lists
            if not isinstance(val, list):
                val = val.split(',')
       
    return val
    

def _sim_event(level, message):
    """Function that can be called externally to signal an event"""
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
                if name in plusargs.keys():
                    if isinstance(plusargs[name], list):
                        plusargs[name].append(value)
                    else:
                        plusargs[name] = [plusargs[name], value]
                else:
                    plusargs[name] = value
            else:
                plusargs[option[1:]] = True
