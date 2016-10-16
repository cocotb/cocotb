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
import re
import string
import sys
import logging
import inspect

from cocotb.utils import get_sim_time

import cocotb.ANSI as ANSI
from pdb import set_trace


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


class InvalidColumnFormat(Exception):
    """Exception used by the ColumnFormatter"""
    pass


class ColumnFormatter(logging.Formatter):
    simtime_search         = '{simtime'
    default_simtime_format = '{:>6.2f}ns'
    fmt_spec_re            = re.compile('((?P<fill>.)?(?P<align>[<>=^]))?(?P<sign>[+\- ])?(?P<alt_form>#)?(?P<zero_fill>0)?(?P<width>\d+)?(?P<comma>,)?(?P<precision>\.\d+)?(?P<type>[bcdeEfFgGnosxX%])?')
    fmt_simtime_re         = re.compile('(?P<spec>.*?)?(?P<resolution>fs|ps|ns|us|ms|sec)')

    def __init__(self, fmt=None, datefmt=None, simtimefmt=None, separator=' | ', prefix="", divider=120, fixed=None, optional=None):
        """Logging formatter that formats fields in columns, ensuring the text does
        not exceed the column width through truncation.  Column formats must be
        specified in the string format style, e.g. {col:8s}

        The 'fixed' columns will always be present and formated.

        The 'optional' columns will only be present formatted if any of the optional
        columns is present in the record.  For any missing from the record, will
        be filled with spaces.

        All columns must have a fixed width with the exception of the last column
        which is defined by the 'fmt' argument.

        Multi-line messages will be properly padded to maintain the column structure

        Kwargs:
                   fmt (str): Fromat for the last column
               datefmt (str): Format string for creating {asctime}
            simtimefmt (str): Format string for creating {simtime}
             separator (str): The string separating the columns
                prefix (str): A prefix that applied to the fmt string if formatting works
               divider (int): Length of the divider/header markers
                fixed (list): List of formats for persistent columns
             optional (list): List of formats for optional columns

        Excetpions:
                      TypeError: 'fixed' and/or 'optional' not a list
            InvalidColumnFormat: Issue processing the column format
        """
        if fixed is not None and not isinstance(fixed, list):
            raise TypeError("Argument 'fixed' must be of type list.")

        if optional is not None and not isinstance(optional, list):
            raise TypeError("Argument 'optional' must be of type list.")

        super(ColumnFormatter, self).__init__(fmt=fmt, datefmt=datefmt, style='{')
        self.simtimefmt   = simtimefmt or self.default_simtime_format
        self._usestime    = super(ColumnFormatter, self).usesTime()
        self._usessimtime = self._fmt.find(self.simtime_search) >= 0
        self._sep = separator
        self._prefix = prefix

        divider = int(divider)
        self._divider = '{{message:-^{}}}'.format(divider)
        self._hdr_len = divider-6
        self._hdr_div = '-'*divider
        self._header  = '-- {{line:{}}} --'.format(self._hdr_len)

        self._fixed = []
        self._optional = []

        self._fixed_pad    = ""
        self._optional_pad = ""
        if fixed is not None:
            for fixed_fmt in fixed:
                col = {}
                col['style']              = logging.StrFormatStyle(fixed_fmt)
                col['fmt']                = col['style']._fmt
                col['parsed'], col['len'] = self._parse_fmt(col['fmt'])
                col['pad']                = ' '*col['len']
                self._usestime            = self._usestime or col['style'].usesTime()
                self._usessimtime         = self._usessimtime or col['fmt'].find(self.simtime_search) >= 0

                self._fixed_pad += '{}{}'.format(col['pad'],self._sep)
                self._fixed.append(col)

        if optional is not None:
            for opt_fmt in optional:
                col = {}
                col['style']              = logging.StrFormatStyle(opt_fmt)
                col['fmt']                = col['style']._fmt
                col['parsed'], col['len'] = self._parse_fmt(col['fmt'])
                col['pad']                = ' '*col['len']
                self._usestime            = self._usestime or col['style'].usesTime()
                self._usessimtime         = self._usessimtime or col['fmt'].find(self.simtime_search) >= 0

                self._optional_pad += '{}{}'.format(col['pad'],self._sep)
                self._optional.append(col)

    def usesTime(self):
        """Returns if the {asctime} field is present in any of the columns"""
        return self._usestime

    def usesSimTime(self):
        """Returns if the {simtime} field is present in any of the columns"""
        return self._usessimtime

    def _formatColumn(self, col, record):
        """Returns a string of the formated column.

        Args:
              col (dict): Column information dictionary
            record (obj): Container with all the parameters for formatting
        """
        return self._trunc(col['style'].format(record),col['len'])


    def formatMessage(self, record):
        """Returns a string of the formatted message with all of the columns.

        Args:
            record (obj): Container with all the parameters for formatting
        """
        s = ""

        for col in self._fixed:
            s += "{}{}".format(self._formatColumn(col,record),self._sep)

        if not hasattr(record, 'include_optional') or record.include_optional:
            include_optional = False
            o = ""
            for col in self._optional:
                try:
                    include_optional = True
                    o += "{}{}".format(self._formatColumn(col,record),self._sep)
                except KeyError:
                    o += "{}{}".format(col['pad'],self._sep)
            if not hasattr(record, 'include_optional'):
                record.include_optional = include_optional

        if record.include_optional:
            s += o
        if not hasattr(record, 'prefix'):
            try:
                record.prefix = self._prefix.format(**record.__dict__)
            except KeyError:
                record.prefix = ""
        msg = super(ColumnFormatter, self).formatMessage(record)

        msg = record.prefix + msg

        s += self._fmt_multi_line_msg(msg,record)

        return s

    def formatHeader(self, record):
        """Returns a string with record.message as a Header

        Args:
            record (obj): Container with all the parameters for formatting
        """
        s = '\n' + self._hdr_div
        for line in record.message.split('\n'):
            while len(line) > self._hdr_len:
                s += '\n' + self._header.format(line=line[:self._hdr_len])
                line = line[self._hdr_len:]
            s += '\n' + self._header.format(line=line)
        s += '\n' + self._hdr_div

        return s

    def formatDivider(self, record):
        """Returns a string with record.message as a Divider

        Args:
            record (obj): Container with all the parameters for formatting
        """
        return self._divider.format(message=record.message)

    def formatSimTime(self, fmt):
        """Returns a formatted string of the current simultaion time

        Args:
            fmt (str): Format string for the simultaion time
        """
        parsed = self.fmt_simtime_re.match(fmt)

        if parsed is None:
            raise ValueError('Invalid SimTime Format String')

        res     = parsed.groupdict()['resolution']
        simtime = get_sim_time(res)

        return fmt.format(simtime)

    def format(self, record):
        """Returns a string of the formatted message with all of the columns,
        including the exception information and the stack information.

        Args:
            record (obj): Container with all the parameters for formatting
        """
        record.message = record.getMessage()

        if not hasattr(record, 'include_optional') and 'COCOTB_REDUCED_LOG_FMT' in os.environ:
            record.include_optional = not bool(int(os.environ['COCOTB_REDUCED_LOG_FMT']))

        if hasattr(record, 'header') and record.header:
            s = self.formatHeader(record)
        elif hasattr(record, 'divider') and record.divider:
            s = self.formatDivider(record)
        else:
            if self.usesTime():
                record.asctime = self.formatTime(record, self.datefmt)
            if self.usesSimTime():
                record.simtime = self.formatSimTime(self.simtimefmt)
            s = self.formatMessage(record)
            if record.exc_info:
                # Cache the traceback text to avoid converting it multiple times
                # (it's constant anyway)
                if not record.exc_text:
                    record.exc_text = self.formatException(record.exc_info)
            if record.exc_text:
                if s[-1:] != "\n":
                    s = s + "\n"
                s = s + self._fmt_multi_line_msg(record.exc_text,
                                                 record,
                                                 pad_first_line=True)
            if record.stack_info:
                if s[-1:] != "\n":
                    s = s + "\n"
                s = s + self._fmt_multi_line_msg(self.formatStack(record.stack_info),
                                                 record,
                                                 pad_first_line=True)
        return s

    def _trunc(self, s, max_len):
        """Returns a string that will not exceed the max_len.

        Args:
                  s (str): The string to truncate
            max_len (int): The maximum allowable string
        """
        if len(s) > max_len:
            return ".." + s[(max_len - 2) * -1:]
        return s

    def _fmt_multi_line_msg(self,msg,record,pad_first_line=False):
        """Returns a formatted string that has been properly padded on each line.

        Args:
                           msg (str): The string to process
                        record (obj): The message record
            pad_first_line (boolean): Indicates whether padding should be applied
                                      to the first line
        """
        pad = '\n' + self._fixed_pad

        if record.include_optional:
            pad += self._optional_pad

        pad += "    " if len(record.prefix) > 0 else ""

        s = pad.join(msg.split('\n'))

        if pad_first_line:
            s = pad[1:] + s
        return s

    def _parse_fmt(self, fmt):
        """Returns the total length of the format string, i.e. column width.

        Args:
            fmt (str): The format string for the column

        Exceptions:
            InvalidColumnFormat: Column width is less than 2 or not a fixed width
        """
        _len = 0
        parsed = []
        for text, name, spec, conv in string.Formatter().parse(fmt):
            _len += len(text)
            if name is not None:
                spec = self._parse_fmt_spec(spec)
                if 'width' in spec:
                    _len += int(spec['width'])
                else:
                    raise InvalidColumnFormat('Width must be defined in the format specifier')
            parsed.append({'text':text,'name':name,'spec':spec,'conv':conv})
        if _len < 2:
            raise InvalidColumnFormat('Column length must be at least 2')

        return parsed, _len

    def _parse_fmt_spec(self, spec):
        """Parses the format specification to get the length of a field.

        Args:
            spec (str): The field specification string

        Exceptions:
            InvalidColumnFormat: Unable to process the format specifier
        """
        match = ColumnFormatter.fmt_spec_re.match(spec)

        if match is None:
            raise InvalidColumnFormat('Unable to parse the format specifier')

        return match.groupdict()

class SimLogFormatter(ColumnFormatter):
    """Log formatter to provide consistent log message handling."""
    _fixed_columns    = ['{simtime:>12s}','{levelname:<10s}']
    _optional_columns = ['{name:<35}', '{filename:>20}:{lineno:<4}', '{funcName:<31}']

    def __init__(self, fmt=None, datefmt=None, simtimefmt=None, separator=' | ', divider=120):
        ColumnFormatter.__init__(self,
                                 fmt=fmt,
                                 datefmt=datefmt,
                                 simtimefmt=simtimefmt,
                                 separator=separator,
                                 prefix="",
                                 divider=divider,
                                 fixed=self._fixed_columns,
                                 optional=self._optional_columns)


class SimColourLogFormatter(SimLogFormatter):

    """Log formatter to provide consistent log message handling."""
    loglevel2colour = {
        logging.DEBUG   :       ANSI.DEFAULT                     + "%s" + ANSI.DEFAULT,
        logging.INFO    :       ANSI.DEFAULT_BG + ANSI.BLUE_FG   + "%s" + ANSI.DEFAULT,
        logging.WARNING :       ANSI.DEFAULT_BG + ANSI.YELLOW_FG + "%s" + ANSI.DEFAULT,
        logging.ERROR   :       ANSI.DEFAULT_BG + ANSI.RED_FG    + "%s" + ANSI.DEFAULT,
        logging.CRITICAL:       ANSI.RED_BG     + ANSI.BLACK_FG  + "%s" + ANSI.DEFAULT}

    def __init__(self, fmt=None, datefmt=None, simtimefmt=None, separator=' | ', divider=120):
        SimLogFormatter.__init__(self,
                                 fmt=fmt,
                                 datefmt=datefmt,
                                 simtimefmt=simtimefmt,
                                 separator=separator,
                                 divider=divider)
        level_pad = self._fixed[1]['pad']
        self._fixed[1]['pad'] = ANSI.DEFAULT + level_pad + ANSI.DEFAULT

        self._fixed_pad = ""
        for col in self._fixed:
            self._fixed_pad += '{}{}'.format(col['pad'],self._sep)

    def _formatColumn(self, col, record):
        """Returns a string of the formated column.

        Args:
              col (dict): Column information dictionary
            record (obj): Container with all the parameters for formatting
        """
        s = SimLogFormatter._formatColumn(self=self, col=col, record=record)

        if id(col) == id(self._fixed[1]):
            s = self.loglevel2colour[record.levelno] % s
        return s


    def _fmt_multi_line_msg(self,msg,record,pad_first_line=False):
        """Returns a formatted string that has been properly padded on each line.

        Args:
                           msg (str): The string to process
                        record (obj): The message record
            pad_first_line (boolean): Indicates whether padding should be applied
                                      to the first line
        """
        return SimLogFormatter._fmt_multi_line_msg(self,
                                                   msg='\n'.join([self.loglevel2colour[record.levelno] % line for line in msg.split('\n')]),
                                                   record=record,
                                                   pad_first_line=pad_first_line)

