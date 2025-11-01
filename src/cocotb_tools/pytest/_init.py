# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Loaded by simulator."""

from __future__ import annotations

import shlex
from functools import wraps
from logging import Logger, getLogger
from typing import cast

import cocotb
from cocotb import simulator
from cocotb_tools.pytest import env
from cocotb_tools.pytest.regression import RegressionManager


def run_regression(_: object) -> None:
    """Run regression using pytest as regression manager for cocotb tests."""
    _setup_logging()

    # Use the same command line arguments as from the main pytest parent process
    args: list[str] = shlex.split(env.as_str("COCOTB_PYTEST_ARGS"))

    # Cocotb runner is using generated JUnit XML results file to determine
    # if executed cocotb tests passed or failed. Test function (cocotb runner)
    # from the main pytest parent process will also fail if any of cocotb test failed.
    results_file: str = env.as_str("COCOTB_RESULTS_FILE")

    if results_file:
        args.append(f"--junit-xml={results_file}")

    cocotb._regression_manager = cast(
        "cocotb.regression.RegressionManager", RegressionManager(*args)
    )

    cocotb._regression_manager.start_regression()


def _setup_logging() -> None:
    # Monkeypatch "gpi" logger with function that also sets a PyGPI-local logger level as an optimization.
    gpi_logger = getLogger("gpi")
    old_setLevel = gpi_logger.setLevel

    @wraps(old_setLevel)
    def setLevel(level: int | str) -> None:
        old_setLevel(level)
        simulator.set_gpi_log_level(gpi_logger.getEffectiveLevel())

    gpi_logger.setLevel = setLevel  # type: ignore[method-assign]

    # Initialize PyGPI logging
    simulator.initialize_logger(_log_from_c, getLogger)


def _log_from_c(
    logger: Logger,
    level: int,
    filename: str,
    lineno: int,
    msg: str,
    function_name: str,
) -> None:
    """
    This is for use from the C world, and allows us to insert C stack
    information.
    """
    if logger.isEnabledFor(level):
        record = logger.makeRecord(
            logger.name, level, filename, lineno, msg, (), None, function_name
        )
        logger.handle(record)
