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
import logging
import os
import random
import sys
import threading
import time
import warnings
from collections.abc import Coroutine
from typing import Dict, List, Optional, Union

import cocotb.handle
from cocotb._deprecation import deprecated
from cocotb.log import default_config
from cocotb.regression import RegressionManager
from cocotb.scheduler import Scheduler
from cocotb.task import Task

from ._version import __version__

# Things we want in the cocotb namespace
from cocotb.decorators import (  # isort: skip # noqa: F401
    coroutine,
    external,
    function,
    test,
)
from cocotb.log import _filter_from_c, _log_from_c  # isort: skip # noqa: F401


def _setup_logging() -> None:
    default_config()
    global log
    log = logging.getLogger(__name__)


# Singleton scheduler instance
# NB this cheekily ensures a singleton since we're replacing the reference
# so that cocotb.scheduler gives you the singleton instance and not the
# scheduler package

scheduler: Optional[Scheduler] = None
"""The global scheduler instance.

This is guaranteed to hold a value at test time.
"""

regression_manager: Optional[RegressionManager] = None
"""The global regression manager instance.

This is guaranteed to hold a value at test time.
"""

argv: Optional[List[str]] = None
"""The argument list as seen by the simulator.

This is guaranteed to hold a value at test time.
"""

argc: Optional[int] = None
"""The length of :data:`cocotb.argv`.

This is guaranteed to hold a value at test time.
"""

plusargs: Optional[Dict[str, Union[bool, str]]] = None
"""A dictionary of "plusargs" handed to the simulation.

See :make:var:`PLUSARGS` for details.
This is guaranteed to hold a value at test time.
"""

LANGUAGE: Optional[str] = os.getenv("TOPLEVEL_LANG")
"""The value of :make:var:`TOPLEVEL_LANG`.

This is guaranteed to hold a value at test time.
"""

SIM_NAME: Optional[str] = None
"""The running simulator product information.

``None`` if :mod:`cocotb` was not loaded from a simulator.
"""

SIM_VERSION: Optional[str] = None
"""The version of the running simulator.

``None`` if :mod:`cocotb` was not loaded from a simulator."""

RANDOM_SEED: Optional[int] = None
"""
The value passed to the Python default random number generator.

See :envvar:`RANDOM_SEED` for details on how the value is computed.
This is guaranteed to hold a value at test time.
"""

_library_coverage = None
""" used for cocotb library coverage """

top: Optional[cocotb.handle.SimHandleBase] = None
r"""
A handle to the :envvar:`TOPLEVEL` entity/module.

This is equivalent to the :term:`DUT` parameter given to cocotb tests, so it can be used wherever that variable can be used.
It is particularly useful for extracting information about the :term:`DUT` in module-level class and function definitions;
and in parameters to :class:`.TestFactory`\ s.
``None`` if :mod:`cocotb` was not loaded from a simulator.
"""


def fork(coro: Union[Task, Coroutine]) -> Task:
    """
    Schedule a coroutine to be run concurrently. See :ref:`coroutines` for details on its use.

    .. deprecated:: 1.7.0
        This function has been deprecated in favor of :func:`cocotb.start_soon` and :func:`cocotb.start`.
        In most cases you can simply substitute ``cocotb.fork`` with ``cocotb.start_soon``.
        For more information on when to use ``start_soon`` vs ``start`` see :ref:`coroutines`.
    """
    warnings.warn(
        "cocotb.fork has been deprecated in favor of cocotb.start_soon and cocotb.start.\n"
        "In most cases you can simply substitute cocotb.fork with cocotb.start_soon.\n"
        "For more information about when you would want to use cocotb.start see the docs,\n"
        "https://docs.cocotb.org/en/latest/coroutines.html#concurrent-execution",
        DeprecationWarning,
        stacklevel=2,
    )
    return scheduler._add(coro)


def start_soon(coro: Union[Task, Coroutine]) -> Task:
    """
    Schedule a coroutine to be run concurrently.

    Note that this is not an async function,
    and the new task will not execute until the calling task yields control.

    .. versionadded:: 1.6.0
    """
    return scheduler.start_soon(coro)


async def start(coro: Union[Task, Coroutine]) -> Task:
    """
    Schedule a coroutine to be run concurrently, then yield control to allow pending tasks to execute.

    The calling task will resume execution before control is returned to the simulator.

    .. versionadded:: 1.6.0
    """
    task = scheduler.start_soon(coro)
    await cocotb.triggers.NullTrigger()
    return task


def create_task(coro: Union[Task, Coroutine]) -> Task:
    """
    Construct a coroutine into a Task without scheduling the Task.

    The Task can later be scheduled with :func:`cocotb.fork`, :func:`cocotb.start`, or
    :func:`cocotb.start_soon`.

    .. versionadded:: 1.6.0
    """
    return cocotb.scheduler.create_task(coro)


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
    """
    with _rlock:

        if "COCOTB_LIBRARY_COVERAGE" in os.environ:
            import coverage

            global _library_coverage
            _library_coverage = coverage.coverage(
                data_file=".coverage.cocotb",
                config_file=False,
                branch=True,
                include=["{}/*".format(os.path.dirname(__file__))],
            )
            _library_coverage.start()

        _initialise_testbench_(argv_)


def _initialise_testbench_(argv_):
    # The body of this function is split in two because no coverage is collected on
    # the function that starts the coverage. By splitting it in two we get coverage
    # on most of the function.

    global argc, argv
    argv = argv_
    argc = len(argv)

    root_name = os.getenv("TOPLEVEL")
    if root_name is not None:
        root_name = root_name.strip()
        if root_name == "":
            root_name = None
        elif "." in root_name:
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

    cocotb.log.info(f"Running on {SIM_NAME} version {SIM_VERSION}")

    memcheck_port = os.getenv("MEMCHECK")
    if memcheck_port is not None:
        mem_debug(int(memcheck_port))

    log.info(
        "Running tests with cocotb v%s from %s"
        % (__version__, os.path.dirname(__file__))
    )

    # Create the base handle type

    _process_plusargs()

    # Seed the Python random number generator to make this repeatable
    global RANDOM_SEED
    RANDOM_SEED = os.getenv("RANDOM_SEED")

    if RANDOM_SEED is None:
        if "ntb_random_seed" in plusargs:
            RANDOM_SEED = eval(plusargs["ntb_random_seed"])
        elif "seed" in plusargs:
            RANDOM_SEED = eval(plusargs["seed"])
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
        raise RuntimeError(f"Can not find root handle ({root_name})")

    global top
    top = cocotb.handle.SimHandle(handle)

    global regression_manager
    regression_manager = RegressionManager.from_discovery(top)

    global scheduler
    scheduler = Scheduler(handle_result=regression_manager._handle_result)

    # start Regression Manager
    regression_manager._execute()


def _sim_event(message):
    """Function that can be called externally to signal an event."""
    from cocotb.result import SimFailure

    # We simply return here as the simulator will exit
    # so no cleanup is needed
    msg = f"Failing test at simulator request before test run completion: {message}"
    scheduler.log.error(msg)
    scheduler._finish_scheduler(SimFailure(msg))


@deprecated("This function is now private")
def process_plusargs() -> None:

    _process_plusargs()


def _process_plusargs() -> None:

    global plusargs

    plusargs = {}

    for option in cocotb.argv:
        if option.startswith("+"):
            if option.find("=") != -1:
                (name, value) = option[1:].split("=", 1)
                plusargs[name] = value
            else:
                plusargs[option[1:]] = True
