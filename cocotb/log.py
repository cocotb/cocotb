''' Copyright (c) 2013 Potential Ventures Ltd
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
import inspect

from cocotb.utils import get_sim_time

import cocotb.ANSI as ANSI
from pdb import set_trace

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
        hdlr = logging.StreamHandler(sys.stdout)
        want_ansi = os.getenv("COCOTB_ANSI_OUTPUT")
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
        self.name = name
        self.handlers = []
        self.disabled = False
        self.filters = []
        self.propagate = False
        logging.__init__(name)
        self.addHandler(hdlr)
        self.setLevel(logging.NOTSET)

""" Need to play with this to get the path of the called back,
    construct our own makeRecord for this """


class SimLog(object):
    def __init__(self, name, ident=None):
        self._ident = ident
        self._name = name
        self.logger = logging.getLogger(name)
        if self._ident is not None:
            self._log_name = "%s.0x%x" % (self._name, self._ident)
        else:
            self._log_name = name

    def _makeRecord(self, level, msg, args, extra=None):
        if self.logger.isEnabledFor(level):
            frame = inspect.stack()[2]
            info = inspect.getframeinfo(frame[0])
            record = self.logger.makeRecord(self._log_name,
                                            level,
                                            info.filename,
                                            info.lineno,
                                            msg,
                                            args,
                                            None,
                                            info.function,
                                            extra)
            self.logger.handle(record)

    def _willLog(self, level):
        """ This is for user from the C world
            it allows a check on if the message will
            be printed. Saves doing lots of work
            for no reason.
        """
        return self.logger.isEnabledFor(level)

    def _printRecord(self, level, filename, lineno, msg, function):
        """ This is for use from the C world and will
            be printed regardless
        """
        if self.logger.isEnabledFor(level):
            record = self.logger.makeRecord(self._log_name,
                                            level,
                                            filename,
                                            lineno,
                                            msg,
                                            None,
                                            None,
                                            function)
            self.logger.handle(record)

    def warn(self, msg, *args, **kwargs):
        self._makeRecord(logging.WARNING, msg, args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._makeRecord(logging.WARNING, msg, args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._makeRecord(logging.DEBUG, msg, args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._makeRecord(logging.ERROR, msg, args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self._makeRecord(logging.CRITICAL, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._makeRecord(logging.INFO, msg, args, **kwargs)

    def __getattr__(self, attribute):
        """Forward any other attribute accesses on to our logger object"""
        return getattr(self.logger, attribute)


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

        prefix = simtime + ' ' + level + ' '
        if not _suppress:
            prefix += self.ljust(record.name, _RECORD_CHARS) + \
                      self.rjust(os.path.split(record.filename)[1], _FILENAME_CHARS) + \
                      ':' + self.ljust(str(record.lineno), _LINENO_CHARS) + \
                      ' in ' + self.ljust(str(record.funcName), _FUNCNAME_CHARS) + ' '

        prefix_len = len(prefix)
        if coloured:
            prefix_len -= (len(level) - _LEVEL_CHARS)
        pad = "\n" + " " * (prefix_len)
        return prefix + pad.join(msg.split('\n'))

    def format(self, record):
        """pretify the log output, annotate with simulation time"""
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
        logging.INFO    :       ANSI.BLUE_FG + "%s" + ANSI.DEFAULT,
        logging.WARNING :       ANSI.YELLOW_FG + "%s" + ANSI.DEFAULT,
        logging.ERROR   :       ANSI.RED_FG + "%s" + ANSI.DEFAULT,
        logging.CRITICAL:       ANSI.RED_BG + ANSI.BLACK_FG + "%s" +
                                ANSI.DEFAULT}

    def format(self, record):
        """pretify the log output, annotate with simulation time"""

        if record.args:
            msg = record.msg % record.args
        else:
            msg = record.msg

        # Need to colour each line in case coloring is applied in the message
        msg = '\n'.join([SimColourLogFormatter.loglevel2colour[record.levelno] % line for line in msg.split('\n')])
        level = (SimColourLogFormatter.loglevel2colour[record.levelno] %
                 record.levelname.ljust(_LEVEL_CHARS))

        return self._format(level, record, msg, coloured=True)
