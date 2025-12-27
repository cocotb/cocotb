# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Loaded by simulator."""

from __future__ import annotations

import sys

import cocotb
from cocotb_tools import _env
from cocotb_tools.pytest._regression import RegressionManager


def run_regression() -> None:
    """Run regression using pytest as regression manager for cocotb tests."""

    # sys.path normally includes "" (the current directory), but does not appear to when Python is embedded.
    # Add it back because users expect to be able to import files in their test directory.
    sys.path.insert(0, "")

    manager: RegressionManager = RegressionManager(
        # Use the same command line arguments as from the main pytest parent process
        *_env.as_args("COCOTB_PYTEST_ARGS"),
        # Node identifier of cocotb runner
        nodeid=_env.as_str("COCOTB_PYTEST_NODEID"),
        # List of cocotb runner keywords
        keywords=_env.as_list("COCOTB_PYTEST_KEYWORDS"),
        # Provide list of test modules (Python modules with cocotb tests) to be loaded
        test_modules=_env.as_list("COCOTB_TEST_MODULES"),
        # Cocotb runner is using generated JUnit XML results file to determine
        # if executed cocotb tests passed or failed. Test function (cocotb runner)
        # from the main pytest parent process will also fail if any of cocotb test failed.
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

    manager.start_regression()
