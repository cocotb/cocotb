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

import os
import sys
import logging
import warnings
from functools import lru_cache

from cocotb.utils import (
    get_sim_time, get_time_from_sim_steps, want_color_output
)

import cocotb.ANSI as ANSI

REDUCED_LOG_FMT = bool("COCOTB_REDUCED_LOG_FMT" in os.environ)

_LEVELNAME_CHARS = len("CRITICAL")  # noqa

# Default log level if not overwritten by the user.
_COCOTB_LOG_LEVEL_DEFAULT = "INFO"


def default_config():
    """ Apply the default cocotb log formatting to the root logger.

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
    log = logging.getLogger('cocotb')

    try:
        # All log levels are upper case, convert the user input for convenience.
        level = os.environ["COCOTB_LOG_LEVEL"].upper()
    except KeyError:
        level = _COCOTB_LOG_LEVEL_DEFAULT

    try:
        log.setLevel(level)
    except ValueError:
        valid_levels = ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG')
        raise ValueError("Invalid log level %r passed through the "
                         "COCOTB_LOG_LEVEL environment variable. Valid log "
                         "levels: %s" % (level, ', '.join(valid_levels)))

    # Notify GPI of log level, which it uses as an optimization to avoid
    # calling into Python.
    from cocotb import simulator
    simulator.log_level(log.getEffectiveLevel())


class SimBaseLog(logging.getLoggerClass()):
    """ This class only exists for backwards compatibility """

    @property
    def logger(self):
        warnings.warn(
            "the .logger attribute should not be used now that `SimLog` "
            "returns a native logger instance directly.",
            DeprecationWarning, stacklevel=2)
        return self

    @property
    def colour(self):
        warnings.warn(
            "the .colour attribute may be removed in future, use the "
            "equivalent `cocotb.utils.want_color_output()` instead",
            DeprecationWarning, stacklevel=2)
        return want_color_output()


# this used to be a class, hence the unusual capitalization
def SimLog(name, ident=None):
    """ Like logging.getLogger, but append a numeric identifier to the name """
    if ident is not None:
        name = "%s.0x%x" % (name, ident)
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
    # Sphinx happy.
    def __init__(self):
        """ Takes no arguments. """
        super().__init__()

    # Justify and truncate
    @staticmethod
    def ljust(string, chars):
        """Left-justify and truncate *string* to *chars* length."""

        if len(string) > chars:
            return "".join(["..", string[(chars - 2) * -1:]])
        return string.ljust(chars)

    @staticmethod
    def rjust(string, chars):
        """Right-justify and truncate *string* to *chars* length."""

        if len(string) > chars:
            return "".join(["..", string[(chars - 2) * -1:]])
        return string.rjust(chars)

    @staticmethod
    def _format_sim_time(record, time_chars=11, time_base="ns"):
        """Return formatted simulator timestamp.

        Uses :attr:`~logging.LogRecord.created_sim_time` and
        :func:`~cocotb.utils.get_time_from_sim_steps`.

        .. versionadded:: 2.0
        """

        sim_time = getattr(record, 'created_sim_time', None)
        if sim_time is None:
            sim_time_str = "  -.--{}".format(time_base)
        else:
            time_with_base = get_time_from_sim_steps(sim_time, time_base)
            sim_time_str = "{:6.2f}{}".format(time_with_base, time_base)
        return sim_time_str.rjust(time_chars)

    @lru_cache(maxsize=128)
    def _format_recordname(self, recordname, chars=35):
        """Return formatted record name *recordname* with *chars* length.

        .. versionadded:: 2.0
        """

        return self.ljust(recordname, chars)

    @lru_cache(maxsize=128)
    def _format_filename(self, filename, lineno, filename_chars=20, lineno_chars=4):
        """Return formatted ``filename:lineno`` pair with *filename_chars* and *lineno_chars* length.

        .. versionadded:: 2.0
        """

        return "".join([self.rjust(os.path.split(filename)[1], filename_chars),
                        ':',
                        self.ljust(str(lineno), lineno_chars)])

    @lru_cache(maxsize=128)
    def _format_funcname(self, funcname, chars=31):
        """Return formatted function name *funcname* with *chars* length.

        .. versionadded:: 2.0
        """

        return self.ljust(funcname, chars)

    def _format_exc_msg(self, record, msg):
        """Return log message *msg* (followed by traceback text if applicable).

        .. versionadded:: 2.0
        """

        # these lines are copied from the built-in logger
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if msg[-1:] != "\n":
                msg = "".join([msg, "\n"])
            msg = "".join([msg, record.exc_text])
        return msg

    def _format_build_line(self, levelname, record, msg, coloured=False):
        """Build the formatted line and return it.

        Uses :func:`_format_sim_time`, :func:`_format_recordname`,
        :func:`_format_filename`, :func:`_format_funcname` and :func:`_format_exc_msg` by default.

        .. versionadded:: 2.0
        """
        prefix = self._format_sim_time(record)
        # NOTE: using a format_levelname here is a bit more complicated since ``levelname`` is
        #       already left-justified and potentially ANSI-colored at this point
        prefix = " ".join([prefix, levelname])
        if not REDUCED_LOG_FMT:
            prefix = "".join([prefix, self._format_recordname(record.name)])
            prefix = "".join([prefix, self._format_filename(record.filename, record.lineno)])
            prefix = " in ".join([prefix, self._format_funcname(record.funcName)])

        msg = self._format_exc_msg(record, msg)

        prefix_len = len(prefix)
        if coloured:
            prefix_len -= (len(levelname) - _LEVELNAME_CHARS)
        pad = "".join(["\n", " " * (prefix_len)])
        return "".join([prefix, pad.join(msg.split('\n'))])

    def format(self, record):
        """Prettify the log output, annotate with simulation time."""

        msg = record.getMessage()
        levelname = record.levelname.ljust(_LEVELNAME_CHARS)

        return self._format_build_line(levelname, record, msg)


class SimColourLogFormatter(SimLogFormatter):
    """Log formatter to provide consistent log message handling."""

    loglevel2colour = {
        logging.DEBUG   :       "%s",
        logging.INFO    :       "%s",
        logging.WARNING :       "".join([ANSI.COLOR_WARNING, "%s", ANSI.COLOR_DEFAULT]),
        logging.ERROR   :       "".join([ANSI.COLOR_ERROR, "%s", ANSI.COLOR_DEFAULT]),
        logging.CRITICAL:       "".join([ANSI.COLOR_CRITICAL, "%s", ANSI.COLOR_DEFAULT]),
    }

    def format(self, record):
        """Prettify the log output, annotate with simulation time."""

        msg = record.getMessage()

        # Need to colour each line in case coloring is applied in the message
        msg = '\n'.join([SimColourLogFormatter.loglevel2colour.get(record.levelno,"%s") % line for line in msg.split('\n')])
        levelname = (SimColourLogFormatter.loglevel2colour[record.levelno] %
                     record.levelname.ljust(_LEVELNAME_CHARS))

        return self._format_build_line(levelname, record, msg, coloured=True)


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
            logger.name,
            level,
            filename,
            lineno,
            msg,
            None,
            None,
            function_name
        )
        logger.handle(record)
