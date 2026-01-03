# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Loaded by simulator."""

from __future__ import annotations

import sys
from logging import getLogger
from random import seed
from time import time
from typing import cast

import cocotb
from cocotb import simtime, simulator
from cocotb._init import (
    _process_packages,
    _process_plusargs,
    _setup_root_handle,
    _sim_event,
)
from cocotb.logging import _setup_gpi_logger
from cocotb_tools.pytest import env
from cocotb_tools.pytest.regression import RegressionManager


def run_regression(argv: list[str]) -> None:
    """Run regression using pytest as regression manager for cocotb tests."""
    _setup_simulation_environment(argv)

    manager: RegressionManager = RegressionManager(
        # Use the same command line arguments as from the main pytest parent process
        *env.as_args("COCOTB_PYTEST_ARGS"),
        # Node identifier of cocotb runner
        nodeid=env.as_str("COCOTB_PYTEST_NODEID"),
        # List of cocotb runner keywords
        keywords=env.as_list("COCOTB_PYTEST_KEYWORDS"),
        # Provide list of test modules (Python modules with cocotb tests) to be loaded
        test_modules=env.as_list("COCOTB_TEST_MODULES"),
        # Cocotb runner is using generated JUnit XML results file to determine
        # if executed cocotb tests passed or failed. Test function (cocotb runner)
        # from the main pytest parent process will also fail if any of cocotb test failed.
        xmlpath=env.as_str("COCOTB_RESULTS_FILE"),
        # Path to directory location from where pytest was invoked
        invocation_dir=env.as_path("COCOTB_PYTEST_DIR"),
        # IPC address (Unix socket, Windows pipe, TCP, ...) to tests reporter
        reporter_address=env.as_str("COCOTB_PYTEST_REPORTER_ADDRESS"),
        # Name of HDL top level design
        toplevel=env.as_str("COCOTB_TOPLEVEL"),
        # Initialization value for the random generator
        seed=cocotb.RANDOM_SEED,
    )

    cocotb._regression_manager = cast("cocotb.regression.RegressionManager", manager)
    cocotb._regression_manager.start_regression()


def _setup_simulation_environment(argv: list[str] | None = None) -> None:
    """Setup minimal required simulation environment for pytest and cocotb."""
    cocotb.simulator.set_sim_event_callback(_sim_event)
    _setup_gpi_logger()

    # sys.path normally includes "" (the current directory), but does not appear to when python is embedded.
    # Add it back because users expect to be able to import files in their test directory.
    sys.path.insert(0, "")

    cocotb.argv = argv or []
    cocotb.is_simulation = True
    cocotb.log = getLogger("test")
    cocotb.RANDOM_SEED = env.as_int("COCOTB_RANDOM_SEED", int(time()))
    cocotb.SIM_NAME = simulator.get_simulator_product().strip()
    cocotb.SIM_VERSION = simulator.get_simulator_version().strip()

    _process_plusargs()
    _process_packages()
    _setup_root_handle()

    simtime._init()
    seed(cocotb.RANDOM_SEED)
