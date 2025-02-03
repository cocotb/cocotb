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
import ast
import logging
import os
import random
import sys
import time
import warnings
from types import SimpleNamespace
from typing import Any, Callable, List, cast

import cocotb
import cocotb._profiling
import cocotb.handle
import cocotb.logging
import cocotb.regression
import cocotb.simulator
from cocotb._scheduler import Scheduler
from cocotb.logging import _filter_from_c, _log_from_c, default_config
from cocotb.regression import RegressionManager, RegressionMode


def _setup_logging() -> None:
    default_config()
    cocotb.log = logging.getLogger("cocotb")
    cocotb.simulator.initialize_logger(_log_from_c, _filter_from_c)


_shutdown_callbacks: List[Callable[[], None]] = []
"""List of callbacks to be called when cocotb shuts down."""


def _register_shutdown_callback(cb: Callable[[], None]) -> None:
    """Register a callback to be called when cocotb shuts down."""
    _shutdown_callbacks.append(cb)


def _shutdown_testbench() -> None:
    """Call all registered shutdown callbacks."""
    while _shutdown_callbacks:
        cb = _shutdown_callbacks.pop(0)
        cb()


def init_package_from_simulation(argv: List[str]) -> None:
    """Initialize the cocotb package from a simulation context."""

    # register a callback to be called if the simulation fails
    cocotb.simulator.set_sim_event_callback(_sim_event)

    cocotb.is_simulation = True

    cocotb.argv = argv

    # sys.path normally includes "" (the current directory), but does not appear to when python is embedded.
    # Add it back because users expect to be able to import files in their test directory.
    sys.path.insert(0, "")

    _setup_logging()

    # From https://www.python.org/dev/peps/pep-0565/#recommended-filter-settings-for-test-runners
    # If the user doesn't want to see these, they can always change the global
    # warning settings in their test module.
    if not sys.warnoptions:
        warnings.simplefilter("default")

    cocotb.SIM_NAME = cocotb.simulator.get_simulator_product().strip()
    cocotb.SIM_VERSION = cocotb.simulator.get_simulator_version().strip()

    cocotb.log.info(f"Running on {cocotb.SIM_NAME} version {cocotb.SIM_VERSION}")

    cocotb._profiling.initialize()
    _register_shutdown_callback(cocotb._profiling.finalize)

    _process_plusargs()
    _process_packages()
    _setup_random_seed()
    _setup_root_handle()
    _start_user_coverage()

    cocotb.log.info(
        f"Initialized cocotb v{cocotb.__version__} from {os.path.dirname(__file__)}"
    )


def run_regression(_: Any) -> None:
    """Setup and run a regression."""

    _setup_regression_manager()

    # setup global scheduler system
    cocotb._scheduler_inst = Scheduler(
        test_complete_cb=cocotb.regression_manager._test_complete
    )

    # start Regression Manager
    cocotb.log.info("Running tests")
    cocotb.regression_manager.start_regression()


def _sim_event(msg: str) -> None:
    """Function that can be called externally to signal an event."""
    # We simply return here as the simulator will exit
    # so no cleanup is needed
    if hasattr(cocotb, "regression_manager"):
        cocotb.regression_manager._fail_simulation(msg)
    else:
        cocotb.log.error(msg)
        _shutdown_testbench()


def _process_plusargs() -> None:
    cocotb.plusargs = {}

    for option in cocotb.argv:
        if option.startswith("+"):
            if option.find("=") != -1:
                (name, value) = option[1:].split("=", 1)
                cocotb.plusargs[name] = value
            else:
                cocotb.plusargs[option[1:]] = True


def _process_packages() -> None:
    pkg_dict = {}

    from cocotb import simulator

    pkgs = simulator.package_iterate()
    if pkgs is None:
        cocotb.packages = SimpleNamespace()
        return

    for pkg in pkgs:
        handle = cast(cocotb.handle.HierarchyObject, cocotb.handle.SimHandle(pkg))
        name = handle._name

        # Icarus doesn't support named access to package objects:
        # https://github.com/steveicarus/iverilog/issues/1038
        # so we cannot lazily create handles
        if cocotb.SIM_NAME == "Icarus Verilog":
            handle._discover_all()
        pkg_dict[name] = handle

    cocotb.packages = SimpleNamespace(**pkg_dict)


def _start_user_coverage() -> None:
    coverage_envvar = os.getenv("COCOTB_USER_COVERAGE")
    if coverage_envvar is None:
        coverage_envvar = os.getenv("COVERAGE")
        if coverage_envvar is not None:
            warnings.warn(
                "COVERAGE is deprecated in favor of COCOTB_USER_COVERAGE",
                DeprecationWarning,
            )
    if coverage_envvar:
        try:
            import coverage
        except ImportError:
            cocotb.log.error(
                "Coverage collection requested but coverage module not available. Install it using `pip install coverage`."
            )
        else:
            config_filepath = os.getenv("COCOTB_COVERAGE_RCFILE")
            if config_filepath is None:
                config_filepath = os.getenv("COVERAGE_RCFILE")
                if config_filepath is not None:
                    warnings.warn(
                        "COVERAGE_RCFILE is deprecated in favor of COCOTB_COVERAGE_RCFILE",
                        DeprecationWarning,
                    )
            if config_filepath is None:
                # Exclude cocotb itself from coverage collection.
                cocotb.log.info(
                    "Collecting coverage of user code. No coverage config file supplied via COCOTB_COVERAGE_RCFILE."
                )
                cocotb_package_dir = os.path.dirname(__file__)
                user_coverage = coverage.coverage(
                    branch=True, omit=[f"{cocotb_package_dir}/*"]
                )
            else:
                cocotb.log.info(
                    "Collecting coverage of user code. Coverage config file supplied."
                )
                # Allow the config file to handle all configuration
                user_coverage = coverage.coverage(config_file=config_filepath)
            user_coverage.start()

            def stop_user_coverage() -> None:
                user_coverage.stop()
                cocotb.log.debug("Writing user coverage data")
                user_coverage.save()

            _register_shutdown_callback(stop_user_coverage)


def _setup_random_seed() -> None:
    seed_envvar = os.getenv("COCOTB_RANDOM_SEED")
    if seed_envvar is None:
        seed_envvar = os.getenv("RANDOM_SEED")
        if seed_envvar is not None:
            warnings.warn(
                "RANDOM_SEED is deprecated in favor of COCOTB_RANDOM_SEED",
                DeprecationWarning,
            )
    if seed_envvar is None:
        if "ntb_random_seed" in cocotb.plusargs:
            plusarg_seed = cocotb.plusargs["ntb_random_seed"]
            if not isinstance(plusarg_seed, str):
                raise TypeError("ntb_random_seed plusarg is not a valid seed value.")
            seed = ast.literal_eval(plusarg_seed)
            if not isinstance(seed, int):
                raise TypeError("ntb_random_seed plusargs is not a valid seed value.")
            cocotb._random_seed = seed
        elif "seed" in cocotb.plusargs:
            plusarg_seed = cocotb.plusargs["seed"]
            if not isinstance(plusarg_seed, str):
                raise TypeError("seed plusarg is not a valid seed value.")
            seed = ast.literal_eval(plusarg_seed)
            if not isinstance(seed, int):
                raise TypeError("seed plusargs is not a valid seed value.")
            cocotb._random_seed = seed
        else:
            cocotb._random_seed = int(time.time())
        cocotb.log.info("Seeding Python random module with %d", cocotb._random_seed)
    else:
        cocotb._random_seed = ast.literal_eval(seed_envvar)
        cocotb.log.info(
            "Seeding Python random module with supplied seed %d", cocotb._random_seed
        )

    random.seed(cocotb._random_seed)


def _setup_root_handle() -> None:
    root_name = os.getenv("COCOTB_TOPLEVEL")
    if root_name is not None:
        root_name = root_name.strip()
        if root_name == "":
            root_name = None
        elif "." in root_name:
            # Skip any library component of the toplevel
            root_name = root_name.split(".", 1)[1]

    from cocotb import simulator

    handle = simulator.get_root_handle(root_name)
    if not handle:
        raise RuntimeError(f"Can not find root handle {root_name!r}")

    cocotb.top = cocotb.handle.SimHandle(handle)


def _setup_regression_manager() -> None:
    cocotb.regression_manager = RegressionManager()

    # discover tests
    module_str = os.getenv("COCOTB_TEST_MODULES", "")
    if not module_str:
        raise RuntimeError(
            "Environment variable COCOTB_TEST_MODULES, which defines the module(s) to execute, is not defined or empty."
        )
    modules = [s.strip() for s in module_str.split(",") if s.strip()]
    cocotb.regression_manager.setup_pytest_assertion_rewriting()
    cocotb.regression_manager.discover_tests(*modules)

    # filter tests
    testcase_str = os.getenv("COCOTB_TESTCASE", "").strip()
    test_filter_str = os.getenv("COCOTB_TEST_FILTER", "").strip()
    if testcase_str and test_filter_str:
        raise RuntimeError("Specify only one of COCOTB_TESTCASE or COCOTB_TEST_FILTER")
    elif testcase_str:
        warnings.warn(
            "TESTCASE is deprecated in favor of COCOTB_TEST_FILTER",
            DeprecationWarning,
        )
        filters = [f"{s.strip()}$" for s in testcase_str.split(",") if s.strip()]
        cocotb.regression_manager.add_filters(*filters)
        cocotb.regression_manager.set_mode(RegressionMode.TESTCASE)
    elif test_filter_str:
        cocotb.regression_manager.add_filters(test_filter_str)
        cocotb.regression_manager.set_mode(RegressionMode.TESTCASE)
