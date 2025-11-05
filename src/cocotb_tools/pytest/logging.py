# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Everything related with logging."""

from __future__ import annotations

import logging
from logging import (
    Filter,
    LogRecord,
    getLogger,
    getLogRecordFactory,
    setLogRecordFactory,
)
from typing import Callable

from _pytest.logging import DEFAULT_LOG_FORMAT, LoggingPlugin
from pytest import Config, Session, hookimpl

import cocotb
from cocotb.simtime import TimeUnit, get_sim_time

COCOTB_LOG_FORMAT: str = (
    "%(sim_time_str)8s%(sim_time_unit)s %(levelname)-8s %(name)s %(message)s"
)


def get_level(name: str) -> int:
    """Get log level based on provided name.

    Args:
        name: Name of log level.

    Returns:
        Integer value of log level.
    """
    return getattr(logging, name.upper(), 0)


class SimContextFilter(Filter):
    """Attach information about simulation to log record using log filter."""

    def __init__(self, config: Config) -> None:
        """Create new instance of simulation context filter.

        Args:
            config: The pytest configuration object.
        """
        self._sim_time_unit: TimeUnit = config.option.cocotb_sim_time_unit
        self._is_simulation: bool = getattr(cocotb, "is_simulation", False)

    def filter(self, record: LogRecord) -> bool:
        """Attach information about simulation to log record."""
        if not hasattr(record, "sim_time"):
            sim_time: int | float | None = self._get_sim_time()
            record.sim_time_unit = self._sim_time_unit

            if sim_time is None:
                record.sim_time = 0
                record.sim_time_str = "-.--"
            else:
                record.sim_time = sim_time
                record.sim_time_str = f"{sim_time:.2f}"

        return True

    def _get_sim_time(self) -> int | float | None:
        if self._is_simulation:
            try:
                return get_sim_time(self._sim_time_unit)
            except RecursionError:
                pass  # If get_sim_time will try to log

        return None


class Logging:
    """Logging plugin to configure logging in pytest environment."""

    def __init__(self, config: Config) -> None:
        """Create new instance of logging plugin."""
        self._filter: Filter = SimContextFilter(config)
        option = config.option

        if not option.log_format and config.getini("log_format") is DEFAULT_LOG_FORMAT:
            option.log_format = COCOTB_LOG_FORMAT

        create_log_record: Callable[..., LogRecord] = getLogRecordFactory()

        def log_record_factory(*args: object, **kwargs: object) -> LogRecord:
            record: LogRecord = create_log_record(*args, **kwargs)

            self._filter.filter(record)

            return record

        setLogRecordFactory(log_record_factory)

        if option.gpi_log_level:
            getLogger("gpi").setLevel(get_level(option.gpi_log_level))

        if option.cocotb_log_level:
            getLogger("cocotb").setLevel(get_level(option.cocotb_log_level))

    @hookimpl(tryfirst=True)
    def pytest_sessionstart(self, session: Session) -> None:
        """Called after the :py:class:`pytest.Session` object has been created and before performing collection and
        entering the run test loop.

        Args:
            session: The pytest session object.
        """
        config: Config = session.config
        plugin: LoggingPlugin | None = config.pluginmanager.get_plugin("logging-plugin")

        if plugin:
            plugin.log_file_handler.addFilter(self._filter)
            plugin.log_cli_handler.addFilter(self._filter)
            plugin.caplog_handler.addFilter(self._filter)
            plugin.report_handler.addFilter(self._filter)
