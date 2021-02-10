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
from typing import Dict, List, Union
from collections.abc import Coroutine

import cocotb.handle
import cocotb.log
from cocotb.scheduler import Scheduler
from cocotb.regression import RegressionManager
from cocotb.decorators import RunningTask

# Things we want in the cocotb namespace
from cocotb.decorators import test, coroutine, hook, function, external  # noqa: F401

from ._version import __version__


def _setup_logging():
    global log

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


# Singleton scheduler instance
# NB this cheekily ensures a singleton since we're replacing the reference
# so that cocotb.scheduler gives you the singleton instance and not the
# scheduler package

scheduler = None  # type: cocotb.scheduler.Scheduler
"""The global scheduler instance."""

regression_manager = None  # type: cocotb.regression.RegressionManager
"""The global regression manager instance."""

argv = None  # type: List[str]
"""The argument list as seen by the simulator"""

argc = None  # type: int
"""The length of :data:`cocotb.argv`"""

plusargs = None  # type: Dict[str, Union[bool, str]]
"""A dictionary of "plusargs" handed to the simulation. See :make:var:`PLUSARGS` for details."""

LANGUAGE = os.getenv("TOPLEVEL_LANG")  # type: str
"""The value of :make:var:`TOPLEVEL_LANG`"""

SIM_NAME = None  # type: str
"""The running simulator product information. ``None`` if :mod:`cocotb` was not loaded from a simulator"""

SIM_VERSION = None  # type: str
"""The version of the running simulator. ``None`` if :mod:`cocotb` was not loaded from a simulator"""

RANDOM_SEED = None  # type: int
"""
The value passed to the Python default random number generator.
See :envvar:`RANDOM_SEED` for details on how the value is computed.
"""

_library_coverage = None
""" used for cocotb library coverage """

top = None  # type: cocotb.handle.SimHandleBase
r"""
A handle to the :envvar:`TOPLEVEL` entity/module.

This is equivalent to the :term:`DUT` parameter given to cocotb tests, so it can be used wherever that variable can be used.
It is particularly useful for extracting information about the :term:`DUT` in module-level class and function definitions;
and in parameters to :class:`.TestFactory`\ s.
``None`` if :mod:`cocotb` was not loaded from a simulator.
"""


def fork(coro: Union[RunningTask, Coroutine]) -> RunningTask:
    """ Schedule a coroutine to be run concurrently. See :ref:`coroutines` for details on its use. """
    return scheduler.add(coro)


# FIXME is this really required?
_rlock = threading.RLock()


def mem_debug(port):
    import cocotb.memdebug
    cocotb.memdebug.start(port)


def _initialise_testbench(argv_):  # pragma: no cover
    """Initialize testbench.

    This function is called after the simulator has elaborated all
    entities and is ready to run the test.

    The test must be defined by the environment variables
    :envvar:`MODULE` and :envvar:`TESTCASE`.

    The environment variable :envvar:`COCOTB_HOOKS`, if present, contains a
    comma-separated list of modules to be executed before the first test.
    """
    with _rlock:

        if "COCOTB_LIBRARY_COVERAGE" in os.environ:
            import coverage

            global _library_coverage
            _library_coverage = coverage.coverage(
                data_file=".coverage.cocotb",
                branch=True,
                include=["{}/*".format(os.path.dirname(__file__))])
            _library_coverage.start()

        return _initialise_testbench_(argv_)


def _initialise_testbench_(argv_):
    # The body of this function is split in two because no coverage is collected on
    # the function that starts the coverage. By splitting it in two we get coverage
    # on most of the function.

    global argc, argv
    argv = argv_
    argc = len(argv)

    root_name = os.getenv("TOPLEVEL")
    if root_name is not None:
        if root_name == "":
            root_name = None
        elif '.' in root_name:
            # Skip any library component of the toplevel
            root_name = root_name.split(".", 1)[1]

    # sys.path normally includes "" (the current directory), but does not appear to when python is embedded.
    # Add it back because users expect to be able to import files in their test directory.
    # TODO: move this to gpi_embed.cpp
    sys.path.insert(0, "")

    _setup_logging()

    # From https://www.python.org/dev/peps/pep-0565/#recommended-filter-settings-for-test-runners
    # If the user doesn't want to see these, they can always change the global
    # warning settings in their test module.
    if not sys.warnoptions:
        warnings.simplefilter("default")

    from cocotb import simulator

    global SIM_NAME, SIM_VERSION
    SIM_NAME = simulator.get_simulator_product().strip()
    SIM_VERSION = simulator.get_simulator_version().strip()

    cocotb.log.info("Running on {} version {}".format(SIM_NAME, SIM_VERSION))

    memcheck_port = os.getenv('MEMCHECK')
    if memcheck_port is not None:
        mem_debug(int(memcheck_port))

    log.info("Running tests with cocotb v%s from %s" %
             (__version__, os.path.dirname(__file__)))

    # Create the base handle type

    process_plusargs()

    global scheduler
    scheduler = Scheduler()

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

    # Setup DUT object
    from cocotb import simulator

    handle = simulator.get_root_handle(root_name)
    if not handle:
        raise RuntimeError("Can not find root handle ({})".format(root_name))

    global top
    top = cocotb.handle.SimHandle(handle)

    try:
        import pytest
    except ImportError:
        log.warning("Pytest not found, assertion rewriting will not occur")
    else:
        try:
            # Install the assertion rewriting hook, which must be done before we
            # import the test modules.
            from _pytest.config import Config
            from _pytest.assertion import install_importhook
            pytest_conf = Config.fromdictargs([], {})
            install_importhook(pytest_conf)
        except Exception:
            log.exception(
                "Configuring the assertion rewrite hook using pytest {} failed. "
                "Please file a bug report!".format(pytest.__version__))

    # start Regression Manager
    global regression_manager
    regression_manager = RegressionManager.from_discovery(top)
    regression_manager.execute()

    return True


def _sim_event(level, message):
    """Function that can be called externally to signal an event."""
    # SIM_INFO = 0
    SIM_TEST_FAIL = 1
    SIM_FAIL = 2
    from cocotb.result import TestFailure, SimFailure

    if level is SIM_TEST_FAIL:
        scheduler.log.error("Failing test at simulator request")
        scheduler._finish_test(TestFailure("Failure from external source: {}".format(message)))
    elif level is SIM_FAIL:
        # We simply return here as the simulator will exit
        # so no cleanup is needed
        msg = "Failing test at simulator request before test run completion: {}".format(message)
        scheduler.log.error(msg)
        scheduler._finish_scheduler(SimFailure(msg))
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
