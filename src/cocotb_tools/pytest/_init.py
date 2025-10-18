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
    args: list[str] = shlex.split(env.as_str("COCOTB_PYTEST_ARGS"))

    results_file: str = env.as_str("COCOTB_RESULTS_FILE")

    if results_file:
        args.append(f"--junit-xml={results_file}")

    if env.exists("COCOTB_TEST_MODULES"):
        args.append("--pyargs")

    cocotb._regression_manager = RegressionManager(*args)
    cocotb._regression_manager.start_regression()
