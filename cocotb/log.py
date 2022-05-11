# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Everything related to logging
"""

import logging
import os
import sys
import typing
import warnings

import cocotb.ANSI as ANSI
from cocotb import simulator
from cocotb.utils import get_sim_time, get_time_from_sim_steps, want_color_output

try:
    _suppress = int(os.environ.get("COCOTB_REDUCED_LOG_FMT", "1"))
except ValueError:
    _suppress = 1

# Column alignment
_LEVEL_CHARS = len("CRITICAL")
_RECORD_CHARS = 34
_FILENAME_CHARS = 20
_LINENO_CHARS = 4
_FUNCNAME_CHARS = 31

# Custom log level
logging.TRACE = 5
logging.addLevelName(5, "TRACE")

# Default log level if not overwritten by the user.
_COCOTB_LOG_LEVEL_DEFAULT = "INFO"


def default_config():
    """Apply the default cocotb log formatting to the root logger.

    This hooks up the logger to write to stdout, using either
    :class:`SimColourLogFormatter` or :class:`SimLogFormatter` depending
    on whether colored output is requested. It also adds a
    :class:`SimTimeContextFilter` filter so that
    :attr:`~logging.LogRecord.created_sim_time` is available to the formatter.

    The logging level for cocotb logs is set based on the
    :envvar:`COCOTB_LOG_LEVEL` environment variable, which defaults to ``INFO``.

    If desired, this logging configuration can be overwritten by calling
    ``logging.basicConfig(..., force=True)`` (in Python 3.8 onwards), or by
    manually resetting the root logger instance.
    An example of this can be found in the section on :ref:`rotating-logger`.

    .. versionadded:: 1.4
    """
    # construct an appropriate handler
    hdlr = logging.StreamHandler(sys.stdout)
    hdlr.addFilter(SimTimeContextFilter())
    if want_color_output():
        hdlr.setFormatter(SimColourLogFormatter())
    else:
        hdlr.setFormatter(SimLogFormatter())

    logging.setLoggerClass(SimBaseLog)  # For backwards compatibility
    logging.basicConfig()
    logging.getLogger().handlers = [hdlr]  # overwrite default handlers

    # apply level settings for cocotb
    log = logging.getLogger("cocotb")

    try:
        # All log levels are upper case, convert the user input for convenience.
        level = os.environ["COCOTB_LOG_LEVEL"].upper()
    except KeyError:
        level = _COCOTB_LOG_LEVEL_DEFAULT

    try:
        log.setLevel(level)
    except ValueError:
        valid_levels = ("CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "TRACE")
        raise ValueError(
            "Invalid log level %r passed through the "
            "COCOTB_LOG_LEVEL environment variable. Valid log "
            "levels: %s" % (level, ", ".join(valid_levels))
        )

    # Notify GPI of log level, which it uses as an optimization to avoid
    # calling into Python.
    logging.getLogger("gpi").setLevel(level)


class SimBaseLog(logging.getLoggerClass()):
    """This class only exists for backwards compatibility"""

    @property
    def logger(self):
        warnings.warn(
            "the .logger attribute should not be used now that `SimLog` "
            "returns a native logger instance directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self

    @property
    def colour(self):
        warnings.warn(
            "the .colour attribute may be removed in future, use the "
            "equivalent `cocotb.utils.want_color_output()` instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return want_color_output()

    def setLevel(self, level: typing.Union[int, str]) -> None:
        super().setLevel(level)
        if self.name == "gpi":
            simulator.log_level(self.getEffectiveLevel())


# this used to be a class, hence the unusual capitalization
def SimLog(name, ident=None):
    """Like logging.getLogger, but append a numeric identifier to the name"""
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
    def __init__(self):
        """"""
        super().__init__()

    def filter(self, record):
        try:
            record.created_sim_time = get_sim_time()
        except RecursionError:
            # get_sim_time may try to log - if that happens, we can't
            # attach a simulator time to this message.
            record.created_sim_time = None
        return True


class SimLogFormatter(logging.Formatter):
    """Log formatter to provide consistent log message handling.

    This will only add simulator timestamps if the handler object this
    formatter is attached to has a :class:`SimTimeContextFilter` filter
    attached, which cocotb ensures by default.
    """

    # Removes the arguments from the base class. Docstring needed to make
    # sphinx happy.
    def __init__(self):
        """Takes no arguments."""
        super().__init__()

    # Justify and truncate
    @staticmethod
    def ljust(string, chars):
        if len(string) > chars:
            return ".." + string[(chars - 2) * -1 :]
        return string.ljust(chars)

    @staticmethod
    def rjust(string, chars):
        if len(string) > chars:
            return ".." + string[(chars - 2) * -1 :]
        return string.rjust(chars)

    def _format(self, level, record, msg, coloured=False):
        sim_time = getattr(record, "created_sim_time", None)
        if sim_time is None:
            sim_time_str = "  -.--ns"
        else:
            time_ns = get_time_from_sim_steps(sim_time, "ns")
            sim_time_str = f"{time_ns:6.2f}ns"
        prefix = (
            sim_time_str.rjust(11)
            + " "
            + level
            + " "
            + self.ljust(record.name, _RECORD_CHARS)
            + " "
        )
        if not _suppress:
            prefix += (
                self.rjust(os.path.split(record.filename)[1], _FILENAME_CHARS)
                + ":"
                + self.ljust(str(record.lineno), _LINENO_CHARS)
                + " in "
                + self.ljust(str(record.funcName), _FUNCNAME_CHARS)
                + " "
            )

        # these lines are copied from the builtin logger
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if msg[-1:] != "\n":
                msg = msg + "\n"
            msg = msg + record.exc_text

        prefix_len = len(prefix)
        if coloured:
            prefix_len -= len(level) - _LEVEL_CHARS
        pad = "\n" + " " * (prefix_len)
        return prefix + pad.join(msg.split("\n"))

    def format(self, record):
        """Prettify the log output, annotate with simulation time"""

        msg = record.getMessage()
        level = record.levelname.ljust(_LEVEL_CHARS)

        return self._format(level, record, msg)


class SimColourLogFormatter(SimLogFormatter):
    """Log formatter to provide consistent log message handling."""

    loglevel2colour = {
        logging.TRACE: "%s",
        logging.DEBUG: "%s",
        logging.INFO: "%s",
        logging.WARNING: ANSI.COLOR_WARNING + "%s" + ANSI.COLOR_DEFAULT,
        logging.ERROR: ANSI.COLOR_ERROR + "%s" + ANSI.COLOR_DEFAULT,
        logging.CRITICAL: ANSI.COLOR_CRITICAL + "%s" + ANSI.COLOR_DEFAULT,
    }

    def format(self, record):
        """Prettify the log output, annotate with simulation time"""

        msg = record.getMessage()

        # Need to colour each line in case coloring is applied in the message
        msg = "\n".join(
            [
                SimColourLogFormatter.loglevel2colour.get(record.levelno, "%s") % line
                for line in msg.split("\n")
            ]
        )
        level = SimColourLogFormatter.loglevel2colour.get(
            record.levelno, "%s"
        ) % record.levelname.ljust(_LEVEL_CHARS)

        return self._format(level, record, msg, coloured=True)


def _filter_from_c(logger_name, level):
    return logging.getLogger(logger_name).isEnabledFor(level)


def _log_from_c(logger_name, level, filename, lineno, msg, function_name):
    """
    This is for use from the C world, and allows us to insert C stack
    information.
    """
    logger = logging.getLogger(logger_name)
    if logger.isEnabledFor(level):
        record = logger.makeRecord(
            logger.name, level, filename, lineno, msg, None, None, function_name
        )
        logger.handle(record)
