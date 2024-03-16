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
import random
import sys
import threading
import time
import warnings
from collections.abc import Coroutine
from types import SimpleNamespace
from typing import Any, Dict, List, Union

import cocotb.handle
from cocotb.logging import default_config
from cocotb.regression import RegressionManager, RegressionMode
from cocotb.scheduler import Scheduler
from cocotb.task import Task

from ._version import __version__

# Things we want in the cocotb namespace
from cocotb.decorators import (  # isort: skip # noqa: F401
    external,
    function,
    test,
    parameterize,
)
from cocotb.logging import _filter_from_c, _log_from_c  # isort: skip # noqa: F401


def _setup_logging() -> None:
    import logging

    default_config()
    global log
    log = logging.getLogger(__name__)


# Singleton scheduler instance
# NB this cheekily ensures a singleton since we're replacing the reference
# so that cocotb.scheduler gives you the singleton instance and not the
# scheduler package

scheduler: Scheduler
"""The global scheduler instance."""

regression_manager: RegressionManager
"""The global regression manager instance."""

argv: List[str]
"""The argument list as seen by the simulator."""

argc: int
"""The length of :data:`cocotb.argv`."""

plusargs: Dict[str, Union[bool, str]]
"""A dictionary of "plusargs" handed to the simulation.

See :make:var:`PLUSARGS` for details.
"""

packages: SimpleNamespace
"""A :class:`python:types.SimpleNamespace` of package handles.

This will be populated with handles at test time if packages can be discovered
via the GPI.

.. versionadded:: 2.0
"""

SIM_NAME: str
"""The running simulator product information."""

SIM_VERSION: str
"""The version of the running simulator."""

_random_seed: int
"""
The value passed to the Python default random number generator.

See :envvar:`RANDOM_SEED` for details on how the value is computed.
This is guaranteed to hold a value at test time.
"""

_library_coverage: Any = None
""" used for cocotb library coverage """

_user_coverage: Any = None
""" used for user code coverage """

top: cocotb.handle.SimHandleBase
r"""
A handle to the :envvar:`TOPLEVEL` entity/module.

This is equivalent to the :term:`DUT` parameter given to cocotb tests, so it can be used wherever that variable can be used.
It is particularly useful for extracting information about the :term:`DUT` in module-level class and function definitions;
and in parameters to :class:`.TestFactory`\ s.
"""


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

    The Task can later be scheduled with :func:`cocotb.start` or :func:`cocotb.start_soon`.

    .. versionadded:: 1.6.0
    """
    return cocotb.scheduler.create_task(coro)


# FIXME is this really required?
_rlock = threading.RLock()


def _initialise_testbench(argv_):  # pragma: no cover
    """Initialize testbench.

    This function is called after the simulator has elaborated all
    entities and is ready to run the test.

    The test must be defined by the environment variables
    :envvar:`MODULE` and :envvar:`TESTCASE`.
    """
    with _rlock:
        try:
            _start_library_coverage()
            _initialise_testbench_(argv_)
        except BaseException:
            log.exception("cocotb testbench initialization failed. Exiting.")
            from cocotb import simulator

            simulator.stop_simulator()
            _stop_library_coverage()


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

    log.info(
        f"Running tests with cocotb v{__version__} from {os.path.dirname(__file__)}"
    )

    # Create the base handle type

    _process_plusargs()
    _process_packages()

    # Seed the Python random number generator to make this repeatable
    global _random_seed
    _random_seed = os.getenv("RANDOM_SEED")

    if _random_seed is None:
        if "ntb_random_seed" in plusargs:
            _random_seed = eval(plusargs["ntb_random_seed"])
        elif "seed" in plusargs:
            _random_seed = eval(plusargs["seed"])
        else:
            _random_seed = int(time.time())
        log.info("Seeding Python random module with %d" % (_random_seed))
    else:
        _random_seed = int(_random_seed)
        log.info("Seeding Python random module with supplied seed %d" % (_random_seed))
    random.seed(_random_seed)

    # Setup DUT object
    handle = simulator.get_root_handle(root_name)
    if not handle:
        raise RuntimeError(f"Can not find root handle ({root_name})")

    global top
    top = cocotb.handle.SimHandle(handle)

    _start_user_coverage()

    global regression_manager
    regression_manager = RegressionManager()

    # discover tests
    module_str = os.getenv("MODULE", "").strip()
    if not module_str:
        raise RuntimeError(
            "Environment variable MODULE, which defines the module(s) to execute, is not defined or empty."
        )
    modules = [s.strip() for s in module_str.split(",") if s.strip()]
    regression_manager.setup_pytest_assertion_rewriting()
    regression_manager.discover_tests(*modules)

    # filter tests
    test_str = os.getenv("TESTCASE", "").strip()
    if test_str:
        filters = [s.strip() for s in test_str.split(",") if s.strip()]
        regression_manager.add_filters(*filters)
        regression_manager.set_mode(RegressionMode.TESTCASE)

    global scheduler
    scheduler = Scheduler(test_complete_cb=regression_manager._test_complete)

    # start Regression Manager
    regression_manager.start_regression()


def _start_library_coverage() -> None:  # pragma: no cover
    if "COCOTB_LIBRARY_COVERAGE" in os.environ:
        try:
            import coverage
        except ImportError:
            log.error(
                "cocotb library coverage collection requested but coverage package not available. Install it using `pip install coverage`."
            )
        else:
            global _library_coverage
            _library_coverage = coverage.coverage(
                data_file=".coverage.cocotb",
                config_file=False,
                branch=True,
                include=[f"{os.path.dirname(__file__)}/*"],
            )
            _library_coverage.start()


def _stop_library_coverage() -> None:
    if _library_coverage is not None:
        # TODO: move this once we have normal shutdown behavior to _sim_event
        _library_coverage.stop()
        _library_coverage.save()  # pragma: no cover


def _sim_event(message):
    """Function that can be called externally to signal an event."""
    from cocotb.result import SimFailure

    # We simply return here as the simulator will exit
    # so no cleanup is needed
    msg = f"Failing test at simulator request before test run completion: {message}"
    if scheduler is not None:
        scheduler.log.error(msg)
        scheduler._finish_scheduler(SimFailure(msg))
    else:
        log.error(msg)
        _stop_user_coverage()
        _stop_library_coverage()


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


def _process_packages() -> None:
    global packages

    pkg_dict = {}

    from cocotb import simulator

    pkgs = simulator.package_iterate()
    if pkgs is None:
        packages = SimpleNamespace()
        return

    for pkg in pkgs:
        handle = cocotb.handle.SimHandle(pkg)
        name = handle._name

        # Icarus doesn't support named access to package objects:
        # https://github.com/steveicarus/iverilog/issues/1038
        # so we cannot lazily create handles
        if SIM_NAME == "Icarus Verilog":
            handle._discover_all()
        pkg_dict[name] = handle

    packages = SimpleNamespace(**pkg_dict)


def _start_user_coverage() -> None:
    if "COVERAGE" in os.environ:
        try:
            import coverage
        except ImportError:
            cocotb.log.error(
                "Coverage collection requested but coverage module not available. Install it using `pip install coverage`."
            )
        else:
            global _user_coverage
            config_filepath = os.getenv("COVERAGE_RCFILE")
            if config_filepath is None:
                # Exclude cocotb itself from coverage collection.
                cocotb.log.info(
                    "Collecting coverage of user code. No coverage config file supplied via COVERAGE_RCFILE."
                )
                cocotb_package_dir = os.path.dirname(__file__)
                _user_coverage = coverage.coverage(
                    branch=True, omit=[f"{cocotb_package_dir}/*"]
                )
            else:
                cocotb.log.info(
                    "Collecting coverage of user code. Coverage config file supplied."
                )
                # Allow the config file to handle all configuration
                _user_coverage = coverage.coverage()
            _user_coverage.start()


def _stop_user_coverage() -> None:
    if _user_coverage is not None:
        _user_coverage.stop()
        cocotb.log.debug("Writing coverage data")
        _user_coverage.save()
