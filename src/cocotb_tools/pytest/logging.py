# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Everything related to logging."""

from __future__ import annotations

from functools import wraps
from logging import Filter, Logger, LogRecord, getLogger

from pytest import Config

from cocotb import simulator
from cocotb.logging import _log_from_c
from cocotb.simtime import TimeUnit, get_sim_time


class SimTimeContextFilter(Filter):
    """A filter to inject simulator times into the log records.

    This uses the approach described in the :ref:`Python logging cookbook <python:filters-contextual>`
    which adds the :attr:`~logging.LogRecord.sim_time` attribute.
    """

    def __init__(self, config: Config) -> None:
        """Create new instance of simulation time context.

        Args:
            config: Pytest configuration object.
        """
        super().__init__()
        self._sim_time_unit: TimeUnit = config.option.cocotb_sim_time_unit

    def filter(self, record: LogRecord) -> bool:
        try:
            record.sim_time_unit = self._sim_time_unit
            record.sim_time = get_sim_time(self._sim_time_unit)
        except RecursionError:
            # get_sim_time may try to log - if that happens, we can't attach a simulator time to this message.
            record.sim_time = None
        return True


def _configure(_: object) -> None:
    gpi_logger: Logger = getLogger("gpi")
    old_setLevel = gpi_logger.setLevel

    @wraps(old_setLevel)
    def setLevel(level: int | str) -> None:
        old_setLevel(level)
        simulator.set_gpi_log_level(gpi_logger.getEffectiveLevel())

    gpi_logger.setLevel = setLevel  # type: ignore[method-assign]

    # Initialize PyGPI logging
    simulator.initialize_logger(_log_from_c, getLogger)
