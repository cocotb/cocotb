# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
Everything related to logging
"""

from __future__ import annotations

import logging
import os
import re
import sys
import time
import warnings
from functools import wraps
from typing import Callable

import cocotb.simtime
from cocotb import simulator
from cocotb._ANSI import ANSI
from cocotb._deprecation import deprecated
from cocotb.simtime import get_sim_time
from cocotb.utils import get_time_from_sim_steps

__all__ = (
    "ANSI",
    "SimLog",
    "SimLogFormatter",
    "SimTimeContextFilter",
    "default_config",
    "strip_ansi",
)

ANSI.__module__ = __name__

# Custom log level
logging.TRACE = 5  # type: ignore[attr-defined]  # type checkers don't like adding module attributes after the fact
logging.addLevelName(5, "TRACE")


strip_ansi: bool = False
"""Whether the default formatter should strip ANSI (color) escape codes from log messages.

Defaults to ``True`` if ``stdout`` is not a TTY and ``False`` otherwise;
but can be overridden with the :envvar:`NO_COLOR` or :envvar:`COCOTB_ANSI_OUTPUT` environment variable.
"""


def default_config(
    reduced_log_fmt: bool = True,
    strip_ansi: bool | None = None,
    prefix_format: str | None = None,
    strip_method: Callable[[str], str] | None = None,
    multiline_indent: int | Callable[[str], int] | None = None,
) -> None:
    """Apply the default cocotb log formatting to the root logger.

    This hooks up the logger to write to stdout, using :class:`SimLogFormatter` for formatting.
    It also adds a :class:`SimTimeContextFilter` filter so that the
    :attr:`~logging.LogRecord.created_sim_time` attribute on :class:`~logging.LogRecord`
    is available to the formatter.

    If desired, this logging configuration can be overwritten by calling
    ``logging.basicConfig(..., force=True)`` (in Python 3.8 onwards),
    or by manually resetting the root logger instance.
    An example of this can be found in the section on :ref:`rotating-logger`.

    Args:
        reduced_log_fmt:
            If ``True``, use a reduced log format that does not include the
            filename, line number, and function name in the log prefix.

            .. versionadded:: 2.0

        strip_ansi:
            If ``True``, strip ANSI (color) escape codes in log messages.
            If ``False``, do not strip ANSI escape codes in log messages.
            If ``None``, use the value of :data:`strip_ansi`.

            .. versionadded:: 2.0

        prefix_format:
            An f-string to build a prefix for each log message.

            .. versionadded:: 2.0

        strip_method:
            A function used to remove nonprintable sequences from a string.
            If ``None``, it defaults to a basic implementation that removes
            at least all the ANSI sequences used by cocotb for coloring.

            .. versionadded:: 2.1

        multiline_indent:
            Controls the indentation of subsequent log lines in a multiline
            log message.
            If the argument is a callable, it will be called every time with
            the stripped formatted prefix string and should return the number
            of spaces to indent.
            If a non-negative integer, it will be used directly as the number
            of spaces to indent.
            If a negative integer, the indentation will be the length of the
            stripped prefix, when formatted with an empty LogRecord. This is
            calculated only on initialization, so it's fast but assumes that
            the prefix length does not change.
            If ``None``, a default length (for builtin prefixes) or a default
            method taking the length of the stripped prefix (for custom
            ``prefix_format``) will be used.

            .. versionadded:: 2.1

    .. versionadded:: 1.4

    .. versionchanged:: 2.0
        Now captures warnings and outputs them through the logging system using
        :func:`logging.captureWarnings`.
    """
    logging.basicConfig()

    hdlr = logging.StreamHandler(sys.stdout)
    hdlr.addFilter(SimTimeContextFilter())
    hdlr.setFormatter(
        SimLogFormatter(
            reduced_log_fmt=reduced_log_fmt,
            strip_ansi=strip_ansi,
            prefix_format=prefix_format,
            strip_method=strip_method,
            multiline_indent=multiline_indent,
        )
    )
    logging.getLogger().handlers = [hdlr]  # overwrite default handlers

    logging.getLogger("cocotb").setLevel(logging.INFO)
    logging.getLogger("gpi").setLevel(logging.INFO)

    logging.captureWarnings(True)


def _init() -> None:
    """cocotb-specific logging setup.

    - Decides whether ANSI escape code stripping is desired by checking
      :envvar:`NO_COLOR` and :envvar:`COCOTB_ANSI_OUTPUT`.
    - Initializes the GPI logger and sets up the GPI logging optimization.
    - Sets the log level of the ``"cocotb"`` and ``"gpi"`` loggers based on
      :envvar:`COCOTB_LOG_LEVEL` and :envvar:`GPI_LOG_LEVEL`, respectively.
    """
    global strip_ansi
    strip_ansi = not sys.stdout.isatty()  # default to color for TTYs
    if os.getenv("NO_COLOR", ""):
        strip_ansi = True
    ansi_output = os.getenv("COCOTB_ANSI_OUTPUT")
    if ansi_output is not None:
        strip_ansi = not int(ansi_output)
    in_gui = os.getenv("GUI")
    if in_gui is not None:
        strip_ansi = bool(int(in_gui))

    # Monkeypatch "gpi" logger with function that also sets a PyGPI-local logger level
    # as an optimization.
    gpi_logger = logging.getLogger("gpi")
    old_setLevel = gpi_logger.setLevel

    @wraps(old_setLevel)
    def setLevel(level: int | str) -> None:
        old_setLevel(level)
        simulator.set_gpi_log_level(gpi_logger.getEffectiveLevel())

    gpi_logger.setLevel = setLevel  # type: ignore[method-assign]

    # Initialize PyGPI logging
    simulator.initialize_logger(_log_from_c, logging.getLogger)

    # Set "cocotb" and "gpi" logger based on environment variables
    def set_level(logger_name: str, envvar: str) -> None:
        log_level = os.environ.get(envvar)
        if log_level is None:
            return

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

    set_level("gpi", "GPI_LOG_LEVEL")
    set_level("cocotb", "COCOTB_LOG_LEVEL")


def _configure(_: object) -> None:
    """Configure basic logging."""
    reduced_log_fmt = True
    try:
        reduced_log_fmt = bool(int(os.environ.get("COCOTB_REDUCED_LOG_FMT", "1")))
    except ValueError:
        pass
    prefix_format = os.environ.get("COCOTB_LOG_PREFIX", None)
    default_config(reduced_log_fmt=reduced_log_fmt, prefix_format=prefix_format)


@deprecated('Use `logging.getLogger(f"{name}.0x{ident:x}")` instead')
def SimLog(name: str, ident: int | None = None) -> logging.Logger:
    """Like :func:`logging.getLogger`, but append a numeric identifier to the name.

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

    This uses the approach described in the :ref:`Python logging cookbook <python:filters-contextual>`
    which adds the :attr:`~logging.LogRecord.created_sim_time` attribute.

    .. versionadded:: 1.4
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.created_sim_time = get_sim_time()
        except RecursionError:
            # get_sim_time may try to log - if that happens, we can't
            # attach a simulator time to this message.
            record.created_sim_time = None
        return True


# Justify and truncate
def _ljust(string: str, chars: int) -> str:
    if len(string) > chars:
        return ".." + string[(chars - 2) * -1 :]
    return string.ljust(chars)


def _rjust(string: str, chars: int) -> str:
    if len(string) > chars:
        return ".." + string[(chars - 2) * -1 :]
    return string.rjust(chars)


class SimLogFormatter(logging.Formatter):
    """Log formatter to provide consistent log message handling.

    This will only add simulator timestamps if the handler object this
    formatter is attached to has a :class:`SimTimeContextFilter` filter
    attached, which cocotb ensures by default.

    See :func:`.default_config` for a description of the arguments.
    """

    loglevel2colour = {
        logging.TRACE: "",  # type: ignore[attr-defined]  # type checkers don't like adding module attributes after the fact
        logging.DEBUG: "",
        logging.INFO: "",
        logging.WARNING: ANSI.YELLOW_FG,
        logging.ERROR: ANSI.RED_FG,
        logging.CRITICAL: ANSI.RED_BG + ANSI.BLACK_FG,
    }

    prefix_func_globals = {
        "time": time,
        "simtime": cocotb.simtime,
        "ANSI": ANSI,
        "ljust": _ljust,
        "rjust": _rjust,
    }

    def __init__(
        self,
        *,
        reduced_log_fmt: bool = True,
        strip_ansi: bool | None = None,
        prefix_format: str | None = None,
        strip_method: Callable[[str], str] | None = None,
        multiline_indent: int | Callable[[str], int] | None = None,
    ) -> None:
        self._reduced_log_fmt = reduced_log_fmt
        self._strip_ansi = strip_ansi

        if strip_method is not None:
            self._strip_method = strip_method
        else:
            ansi_escape_pattern = re.compile(
                r"""
                    \x1B
                    (?: # either 7-bit C1, two bytes, ESC Fe (omitting CSI)
                        [@-Z\\-_]
                    | # or 7-bit CSI (ESC [) + control codes
                        \[
                        [0-?]*  # Parameter bytes
                        [ -/]*  # Intermediate bytes
                        [@-~]   # Final byte
                    )
                """,
                re.VERBOSE,
            )
            self._strip_method = lambda s: ansi_escape_pattern.sub("", s)

        if prefix_format is None:
            prefix_format = "{simtime_ns:>11} {level_color_start}{record.levelname:<8}{level_color_end} {ljust(record.name, 34)} "
            if not self._reduced_log_fmt:
                prefix_format = (
                    prefix_format
                    + "{rjust(record.filename, 20)}:{record.lineno:<4} in {ljust(str(record.funcName), 31)} "
                )
            if multiline_indent is None:
                # The default prefix_formats length is fixed, so unless explicitly
                # overridden, precompute indentation on initialization.
                multiline_indent = -1

        self._prefix_func = eval(
            f"lambda record, simtime_ns, level_color_start, level_color_end: f'''{prefix_format}'''",
            type(self).prefix_func_globals,
        )

        if isinstance(multiline_indent, int) and multiline_indent < 0:
            # Compute the indentation based on the length of the prefix
            # when formatted with an empty LogRecord.
            record = logging.getLogger().makeRecord(
                "", logging.INFO, "", 0, "", (), None, func=""
            )
            multiline_indent = len(
                self._strip_method(self._prefix_func(record, "", "", ""))
            )

        if multiline_indent is None:
            self._multiline_indent: int | Callable[[str], int] = len
        else:
            self._multiline_indent = multiline_indent

    def strip_ansi(self) -> bool:
        return strip_ansi if self._strip_ansi is None else self._strip_ansi

    # Justify and truncate
    @staticmethod
    def ljust(string: str, chars: int) -> str:
        return _ljust(string, chars)

    @staticmethod
    def rjust(string: str, chars: int) -> str:
        return _rjust(string, chars)

    def formatPrefix(
        self,
        record: logging.LogRecord,
        level_color_start: str,
        level_color_end: str,
    ) -> str:
        sim_time = getattr(record, "created_sim_time", None)
        if sim_time is None:
            simtime_ns = "-.--ns"
        else:
            time_ns = get_time_from_sim_steps(sim_time, "ns")
            simtime_ns = f"{time_ns:.2f}ns"

        return self._prefix_func(record, simtime_ns, level_color_start, level_color_end)

    def formatExcInfo(self, record: logging.LogRecord) -> str:
        msg = ""

        # these lines are copied and updated from the built-in logger
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            msg += record.exc_text
        if record.stack_info:
            if not msg.endswith("\n"):
                msg += "\n"
            msg += self.formatStack(record.stack_info)

        return msg

    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()

        if self.strip_ansi():
            level_color_start = ""
            level_color_end = ""
        else:
            level_color_start = self.loglevel2colour.get(record.levelno, "")
            level_color_end = ANSI.DEFAULT if level_color_start else ""

        prefix = self.formatPrefix(record, level_color_start, level_color_end)

        if self.strip_ansi():
            output = self._strip_method(f"{prefix}{msg}")
        elif level_color_start:
            # NOTE: this handles the case where the string to log applies some
            # custom coloring, but then reverts to default. The default should
            # be this log level's default and not the terminal's. This assumes
            # that ANSI.DEFAULT is used to revert.
            output = f"{prefix}{level_color_start}{msg.replace(ANSI.DEFAULT, level_color_start)}{ANSI.DEFAULT}"
        else:
            # Just in case the log message itself contains ANSI codes,
            # always revert to default at the end.
            output = f"{prefix}{msg}{ANSI.DEFAULT}"

        exc_info = self.formatExcInfo(record)
        if exc_info:
            multiline = True
            output = f"{output}\n{exc_info}"
        else:
            multiline = "\n" in msg

        if (not multiline) or (self._multiline_indent == 0):
            return output

        lines = output.splitlines()

        # add padding to each line of message
        if isinstance(self._multiline_indent, int):
            indent = self._multiline_indent
        else:
            indent = self._multiline_indent(self._strip_method(prefix))
        pad = "\n" + " " * indent

        return pad.join(lines)


class SimColourLogFormatter(SimLogFormatter):
    """Log formatter similar to :class:`SimLogFormatter`, but with colored output by default.

    .. deprecated:: 2.0
        Use :class:`!SimLogFormatter` with ``strip_ansi=False`` instead.
    """

    def __init__(
        self,
        *,
        reduced_log_fmt: bool = True,
        strip_ansi: bool | None = False,
        prefix_format: str | None = None,
    ) -> None:
        warnings.warn(
            "SimColourLogFormatter is deprecated and will be removed in a future release. "
            "Use SimLogFormatter with `strip_ansi=False` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            reduced_log_fmt=reduced_log_fmt,
            strip_ansi=strip_ansi,
            prefix_format=prefix_format,
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
