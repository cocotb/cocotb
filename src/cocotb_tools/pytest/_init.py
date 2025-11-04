# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Loaded by simulator."""

from __future__ import annotations

from typing import cast

import cocotb
from cocotb_tools.pytest import env
from cocotb_tools.pytest.regression import RegressionManager


def run_regression(_: object) -> None:
    """Run regression using pytest as regression manager for cocotb tests."""
    manager: RegressionManager = RegressionManager(
        # Use the same command line arguments as from the main pytest parent process
        *env.as_args("COCOTB_PYTEST_ARGS"),
        # Provide list of test modules (Python modules with cocotb tests) to be loaded
        test_modules=env.as_list("COCOTB_TEST_MODULES"),
        # Cocotb runner is using generated JUnit XML results file to determine
        # if executed cocotb tests passed or failed. Test function (cocotb runner)
        # from the main pytest parent process will also fail if any of cocotb test failed.
        xmlpath=env.as_str("COCOTB_RESULTS_FILE"),
    )

    cocotb._regression_manager = cast("cocotb.regression.RegressionManager", manager)
    cocotb._regression_manager.start_regression()
