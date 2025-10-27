# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Loaded by simulator."""

from __future__ import annotations

import shlex

import cocotb
from cocotb_tools.pytest import env
from cocotb_tools.pytest.regression import RegressionManager


def run_regression(_: object) -> None:
    """Run regression using pytest as regression manager for cocotb tests."""
    # Use the same command line arguments as from the main pytest parent process
    args: list[str] = shlex.split(env.as_str("COCOTB_PYTEST_ARGS"))

    # Cocotb runner is using generated JUnit XML results file to determine
    # if executed cocotb tests passed or failed. Test function (cocotb runner)
    # from the main pytest parent process will also fail if any of cocotb test failed.
    results_file: str = env.as_str("COCOTB_RESULTS_FILE")

    if results_file:
        args.append(f"--junit-xml={results_file}")

    cocotb._regression_manager = RegressionManager(*args)
    cocotb._regression_manager.start_regression()
