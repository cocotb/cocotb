# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
Everything related to logging
"""

import io
import logging
import logging.config
import os
import sys
import time
import traceback
import warnings
from functools import cached_property, wraps
from types import TracebackType
from typing import Dict, Optional, Union, cast

from cocotb import _ANSI, simulator
from cocotb._deprecation import deprecated
from cocotb._typing import TimeUnit
from cocotb._utils import want_color_output
from cocotb.utils import get_sim_time, get_time_from_sim_steps

__all__ = (
    "SimColourLogFormatter",
    "SimLog",
    "SimLogFormatter",
    "SimTimeContextFilter",
    "default_config",
)

# Custom log level
logging.TRACE = 5  # type: ignore[attr-defined]  # type checkers don't like adding module attributes after the fact
logging.addLevelName(5, "TRACE")

_reduced_fmt_env = os.environ.get("COCOTB_REDUCED_LOG_FMT")
if _reduced_fmt_env is not None:
    warnings.warn(
        "`COCOTB_REDUCED_LOG_FMT` is deprecated. Use COCOTB_LOG_CONFIG instead.",
        DeprecationWarning,
    )
    _reduced_fmt = bool(int(_reduced_fmt_env))
else:
    _reduced_fmt = False


def default_config() -> None:
    """Apply the default cocotb log formatting to the root logger.

    This hooks up the logger to write to stdout, using either
    :class:`SimColourLogFormatter` or :class:`SimLogFormatter` depending
    on whether colored output is requested. It also adds a
    :class:`SimTimeContextFilter` filter so that
    :attr:`~logging.LogRecord.created_sim_time` is available to the formatter.

    If desired, this logging configuration can be overwritten by calling
    ``logging.basicConfig(..., force=True)`` (in Python 3.8 onwards), or by
    manually resetting the root logger instance.
    An example of this can be found in the section on :ref:`rotating-logger`.

    .. versionadded:: 1.4

    .. versionchanged:: 2.0
        No longer set the log level of the ``cocotb`` and ``gpi`` loggers.
    """
    logging.basicConfig()

    hdlr = logging.StreamHandler(sys.stdout)
    hdlr.addFilter(SimTimeContextFilter())
    hdlr.setFormatter(SimLogFormatter(color=want_color_output()))  # type: ignore
    logging.getLogger().handlers = [hdlr]  # overwrite default handlers


def _init(_: object) -> None:
    """Set cocotb and pygpi log levels."""

    # Monkeypatch "gpi" logger with function that also sets a PyGPI-local logger level
    # as an optimization.
    gpi_logger = logging.getLogger("gpi")
    old_setLevel = gpi_logger.setLevel

    @wraps(old_setLevel)
    def setLevel(level: Union[int, str]) -> None:
        old_setLevel(level)
        simulator.set_gpi_log_level(gpi_logger.getEffectiveLevel())

    gpi_logger.setLevel = setLevel  # type: ignore[method-assign]

    # Initialize PyGPI logging
    simulator.initialize_logger(_log_from_c, logging.getLogger)

    # Set "cocotb" and "gpi" logger based on environment variables
    def set_level(logger_name: str, envvar: str, default_level: str) -> None:
        log_level = os.environ.get(envvar, default_level)
        log_level = log_level.upper()

        logger = logging.getLogger(logger_name)

        try:
            logger.setLevel(log_level)
        except ValueError:
            valid_levels = ", ".join(
                ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE", "NOTSET")
            )
            raise ValueError(
                f"Invalid log level {log_level!r} passed through the "
                f"{envvar} environment variable. Valid log "
                f"levels: {valid_levels}"
            ) from None

    set_level("gpi", "GPI_LOG_LEVEL", "INFO")
    set_level("cocotb", "COCOTB_LOG_LEVEL", "INFO")


def _setup_formatter(_: object) -> None:
    """Setup cocotb's logging formatter."""
    log_config = os.environ.get("COCOTB_LOG_CONFIG")
    if log_config is None:
        default_config()
    else:
        logging.config.fileConfig(log_config)


@deprecated('Use `logging.getLogger(f"{name}.0x{ident:x}")` instead')
def SimLog(name: str, ident: Union[int, None] = None) -> logging.Logger:
    """Like logging.getLogger, but append a numeric identifier to the name.

    Args:
        name: Logger name.
        ident: Unique integer identifier.

    Returns:
        The Logger named ``{name}.0x{ident:x}``.

    .. deprecated:: 2.0

        Use ``logging.getLogger(f"{name}.0x{ident:x}")`` instead.
    """
    if ident is not None:
        name = f"{name}.0x{ident:x}"
    return logging.getLogger(name)


class SimTimeContextFilter(logging.Filter):
    """
    A filter to inject simulator times into the log records.

    This uses the approach described in the :ref:`Python logging cookbook <python:filters-contextual>`.

    This adds the :attr:`~logging.LogRecord.created_sim_time` attribute.

    .. versionadded:: 1.4
    """

    # needed to make our docs render well
    def __init__(self) -> None:
        """"""
        super().__init__()

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.created_sim_time = get_sim_time()
        except RecursionError:
            # get_sim_time may try to log - if that happens, we can't
            # attach a simulator time to this message.
            record.created_sim_time = None
        return True


def _vfstrfmt(fmt: str, args: Dict[str, object]) -> str:
    return eval(f'f"""{fmt}"""', args)


class SimLogFormatter:
    loglevel2colour = {
        logging.TRACE: "",  # type: ignore[attr-defined]  # type checkers don't like adding module attributes after the fact
        logging.DEBUG: "",
        logging.INFO: "",
        logging.WARNING: _ANSI.COLOR_WARNING,
        logging.ERROR: _ANSI.COLOR_ERROR,
        logging.CRITICAL: _ANSI.COLOR_CRITICAL,
    }

    time_converter = time.localtime

    class _SimTimeConverter(dict):
        def __init__(self, steps: int) -> None:
            self._steps = steps

        def __getitem__(self, key: str) -> float:
            if key == "step":
                return self._steps
            else:
                return get_time_from_sim_steps(self._steps, cast("TimeUnit", key))

    default_prefix = "{sim_time:>11} {levelname:<8} {name[-34:]:<34} " + (
        ""
        if _reduced_fmt
        else "{filename[-20:]:>20}:{lineno:4} in {funcName[-31:]:31} "
    )
    default_datefmt = "%Y-%m-%d %H:%M:%S"
    default_sim_time_fmt = "{ns:.2f}ns"
    default_empty_sim_time_fmt = "-.--ns"

    def __init__(
        self,
        *,
        prefix_fmt: Optional[str] = None,
        date_fmt: Optional[str] = None,
        sim_time_fmt: Optional[str] = None,
        empty_sim_time_fmt: Optional[str] = None,
        color: bool = False,
    ) -> None:
        self.prefix_fmt = prefix_fmt if prefix_fmt is not None else self.default_prefix
        self.date_fmt = date_fmt if date_fmt is not None else self.default_datefmt
        self.sim_time_fmt = (
            sim_time_fmt if sim_time_fmt is not None else self.default_sim_time_fmt
        )
        self.empty_sim_time_fmt = (
            empty_sim_time_fmt
            if empty_sim_time_fmt is not None
            else self.default_empty_sim_time_fmt
        )
        self.color = color

    def _format_time(self, record: logging.LogRecord) -> str:
        ct = type(self).time_converter(record.created)
        return time.strftime(self.date_fmt, ct)

    def _format_sim_time(self, record: logging.LogRecord) -> str:
        sim_time = cast("int | None", getattr(record, "created_sim_time", None))
        if sim_time is None:
            return _vfstrfmt(self.empty_sim_time_fmt, {})
        else:
            return _vfstrfmt(self.sim_time_fmt, type(self)._SimTimeConverter(sim_time))

    @cached_property
    def _uses_time(self) -> bool:
        return "asctime" in self.prefix_fmt

    @cached_property
    def _uses_sim_time(self) -> bool:
        return "sim_time" in self.prefix_fmt

    def _format_message(self, record: logging.LogRecord) -> str:
        prefix = _vfstrfmt(self.prefix_fmt, vars(record))

        # add padding to each line of message
        msg_lines = record.getMessage().split("\n")
        prefix_len = sum(c.isprintable() for c in prefix)
        pad = "\n" + " " * prefix_len
        msg = pad.join(msg_lines)

        if self.color:
            highlight = self.loglevel2colour.get(record.levelno, "%s")
            msg = f"{highlight}{msg}{_ANSI.COLOR_DEFAULT}"

        return prefix + msg

    def _format_exception(
        self,
        ei: "tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None]",
    ) -> str:
        with io.StringIO() as sio:
            traceback.print_exception(ei[0], ei[1], ei[2], None, sio)
            s = sio.getvalue()
        if s.endswith("\n"):
            s = s[:-1]
        return s

    def _format_stack(self, stack_info: str) -> str:
        return stack_info

    def format(self, record: logging.LogRecord) -> str:
        if self._uses_sim_time:
            record.sim_time = self._format_sim_time(record)

        if self._uses_time:
            record.asctime = self._format_time(record)

        s = self._format_message(record)

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self._format_exception(record.exc_info)

        if record.exc_text:
            if not s.endswith("\n"):
                s = s + "\n"
            s = s + record.exc_text

        if record.stack_info:
            if not s.endswith("\n"):
                s = s + "\n"
            s = s + self._format_stack(record.stack_info)

        return s


class SimColourLogFormatter(SimLogFormatter):
    def __init__(
        self,
        *,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        sim_time_fmt: Optional[str] = None,
        empty_sim_time_fmt: Optional[str] = None,
        color: bool = True,
    ) -> None:
        super().__init__(
            prefix_fmt=fmt,
            date_fmt=datefmt,
            sim_time_fmt=sim_time_fmt,
            empty_sim_time_fmt=empty_sim_time_fmt,
            color=color,
        )


def _log_from_c(
    logger: logging.Logger,
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
