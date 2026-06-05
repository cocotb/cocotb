# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Initialization entry point loaded by the simulator.

This module initializes the cocotb regression manager when the simulation starts,
parsing environment variables and configuring the pytest session structure inside the simulator process.
"""

from __future__ import annotations

import sys
from typing import cast

import cocotb
import cocotb.regression
from cocotb_tools import _env
from cocotb_tools.pytest._regression import RegressionManager


def run_regression() -> None:
    """Run the regression test suite inside the simulator process.

    This function configures the global regression manager with pytest settings, initializes the cocotb environment, and starts the test execution loop.
    """
    # sys.path normally includes "" (the current directory), but does not appear to when Python is embedded.
    # Add it back because users expect to be able to import files in their test directory.
    sys.path.insert(0, "")

    manager: RegressionManager = RegressionManager(
        # Use the same command line arguments as from the main pytest parent process
        *_env.as_args("COCOTB_PYTEST_ARGS"),
        # Node identifier of simulation process
        nodeid=_env.as_str("PYTEST_CURRENT_TEST").removesuffix(" (call)"),
        # List of additional keywords for cocotb tests
        keywords=_env.as_list("COCOTB_PYTEST_KEYWORDS"),
        # Provide list of test modules (Python modules with cocotb tests) to be loaded
        test_modules=_env.as_list("COCOTB_TEST_MODULES"),
        # Cocotb runner is using generated JUnit XML results file to determine
        # if executed cocotb tests passed or failed.
        # Test function from the main pytest parent process will also fail if any of cocotb test failed
        xmlpath=_env.as_str("COCOTB_RESULTS_FILE"),
        # Path to directory location from where pytest was invoked
        invocation_dir=_env.as_path("COCOTB_PYTEST_DIR"),
        # IPC address (Unix socket, Windows pipe, TCP, ...) to tests reporter
        reporter_address=_env.as_str("COCOTB_PYTEST_REPORTER_ADDRESS"),
        # Name of HDL top level design
        toplevel=_env.as_str("COCOTB_TOPLEVEL"),
        # Initialization value for the random generator
        seed=cocotb.RANDOM_SEED,
        # If defined, convert all absolute paths to relative ones
        relative_to=_env.as_str("COCOTB_RESULTS_RELATIVE_TO"),
        # List of file attachments to be included in created test reports
        attachments=_env.as_list("COCOTB_RESULTS_ATTACHMENTS"),
    )

    cocotb.regression._manager_inst = cast(
        "cocotb.regression.RegressionManager", manager
    )

    manager.start_regression()
