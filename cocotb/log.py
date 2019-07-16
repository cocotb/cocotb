''' Copyright (c) 2013, 2018 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""
Everything related to logging
"""

import os
import sys
import logging
import warnings

from cocotb.utils import get_sim_time

import cocotb.ANSI as ANSI

if "COCOTB_REDUCED_LOG_FMT" in os.environ:
    _suppress = True
else:
    _suppress = False

# Column alignment
_LEVEL_CHARS    = len("CRITICAL")  # noqa
_RECORD_CHARS   = 35  # noqa
_FILENAME_CHARS = 20  # noqa
_LINENO_CHARS   = 4  # noqa
_FUNCNAME_CHARS = 31  # noqa


class SimBaseLog(logging.getLoggerClass()):
    def __init__(self, name):
        super(SimBaseLog, self).__init__(name)

        # customizations of the defaults
        hdlr = logging.StreamHandler(sys.stdout)
        want_ansi = os.getenv("COCOTB_ANSI_OUTPUT") and not os.getenv("GUI")
        if want_ansi is None:
            want_ansi = sys.stdout.isatty()  # default to ANSI for TTYs
        else:
            want_ansi = want_ansi == '1'
        if want_ansi:
            hdlr.setFormatter(SimColourLogFormatter())
            self.colour = True
        else:
            hdlr.setFormatter(SimLogFormatter())
            self.colour = False

        self.propagate = False
        self.addHandler(hdlr)

    def _logFromC(self, level, filename, lineno, msg, function):
        """
        This is for use from the C world, and allows us to insert C stack
        information.
        """
        if self.isEnabledFor(level):
            record = self.makeRecord(
                self.name,
                level,
                filename,
                lineno,
                msg,
                None,
                None,
                function
            )
            self.handle(record)

    @property
    def logger(self):
        warnings.warn(
            "the .logger attribute should not be used now that `SimLog` "
            "returns a native logger instance directly.",
            DeprecationWarning)
        return self


# this used to be a class, hence the unusual capitalization
def SimLog(name, ident=None):
    """ Like logging.getLogger, but append a numeric identifier to the name """
    if ident is not None:
        name = "%s.0x%x" % (name, ident)
    return logging.getLogger(name)


class SimLogFormatter(logging.Formatter):
    """Log formatter to provide consistent log message handling."""

    # Justify and truncate
    @staticmethod
    def ljust(string, chars):
        if len(string) > chars:
            return ".." + string[(chars - 2) * -1:]
        return string.ljust(chars)

    @staticmethod
    def rjust(string, chars):
        if len(string) > chars:
            return ".." + string[(chars - 2) * -1:]
        return string.rjust(chars)

    def _format(self, level, record, msg, coloured=False):
        time_ns = get_sim_time('ns')
        simtime = "%6.2fns" % (time_ns)
        prefix = simtime.rjust(11) + ' ' + level + ' '
        if not _suppress:
            prefix += self.ljust(record.name, _RECORD_CHARS) + \
                      self.rjust(os.path.split(record.filename)[1], _FILENAME_CHARS) + \
                      ':' + self.ljust(str(record.lineno), _LINENO_CHARS) + \
                      ' in ' + self.ljust(str(record.funcName), _FUNCNAME_CHARS) + ' '

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
            prefix_len -= (len(level) - _LEVEL_CHARS)
        pad = "\n" + " " * (prefix_len)
        return prefix + pad.join(msg.split('\n'))

    def format(self, record):
        """Prettify the log output, annotate with simulation time"""
        if record.args:
            msg = record.msg % record.args
        else:
            msg = record.msg

        msg = str(msg)
        level = record.levelname.ljust(_LEVEL_CHARS)

        return self._format(level, record, msg)


class SimColourLogFormatter(SimLogFormatter):

    """Log formatter to provide consistent log message handling."""
    loglevel2colour = {
        logging.DEBUG   :       "%s",
        logging.INFO    :       ANSI.COLOR_INFO + "%s" + ANSI.COLOR_DEFAULT,
        logging.WARNING :       ANSI.COLOR_WARNING + "%s" + ANSI.COLOR_DEFAULT,
        logging.ERROR   :       ANSI.COLOR_ERROR + "%s" + ANSI.COLOR_DEFAULT,
        logging.CRITICAL:       ANSI.COLOR_CRITICAL + "%s" + ANSI.COLOR_DEFAULT,
    }

    def format(self, record):
        """Prettify the log output, annotate with simulation time"""

        if record.args:
            msg = record.msg % record.args
        else:
            msg = record.msg

        # Need to colour each line in case coloring is applied in the message
        msg = '\n'.join([SimColourLogFormatter.loglevel2colour[record.levelno] % line for line in msg.split('\n')])
        level = (SimColourLogFormatter.loglevel2colour[record.levelno] %
                 record.levelname.ljust(_LEVEL_CHARS))

        return self._format(level, record, msg, coloured=True)
