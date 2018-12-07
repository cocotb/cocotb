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
import os.path
import re
import string
import sys
import logging
import logging.config
import inspect

import traceback

try:
    from StringIO import StringIO
except ImportError:
    from io       import StringIO

from cocotb.utils import get_sim_time, allow_ansi

import cocotb.ANSI as ANSI
from pdb import set_trace

# Import the default logging levels to be available in this package
from logging import CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET

# Define additional Logging Levels
VERBOSE    = 15
DIAGNOSTIC = 5

_levelToName = {
    VERBOSE:    'VERBOSE',
    DIAGNOSTIC: 'DIAGNOSTIC'
}

# Register the new levels
for l,n in iter(_levelToName.items()): logging.addLevelName(l,n)

_DEFAULT_CONFIG = """
[loggers]
keys=root,top

[handlers]
keys=console

[formatters]
keys=sim_log, sim_log_colour

[logger_root]
level=WARNING
handlers=

[logger_top]
level={level}
handlers=console
propagate=0
qualname={top}

[handler_console]
class=StreamHandler
level=NOTSET
formatter={formatter}
args=(sys.stdout,)

[formatter_sim_log]
class=cocotb.log.SimLogFormatter

[formatter_sim_log_colour]
class=cocotb.log.SimColourLogFormatter
"""

_top_name   = None
_top_logger = None
_init_cbs   = []
_notify_cbs = []

def register_level_notify_cb(logger, f):
    """Register a callback function for level change notifications.

    Args:
        logger (obj): The logger monitored for level changes
        f      (fun): Function to notify, i.e. f(level)
    """
    global _notify_cbs
    _notify_cbs.append({'log':logger, 'level':logger.getEffectiveLevel(), 'fun':f})

def _notify_level_change():
    """Notify callbacks if the level has changed for the logger"""
    global _notify_cbs
    for cb in _notify_cbs:
        lvl = cb['log'].getEffectiveLevel()
        if lvl != cb['level']:
            cb['level'] = lvl
            cb['fun'](lvl)

def register_initialize_cb(f):
    """Decorator to register function callback when logging has been initialized.
    If logging has already been initialized, the function will be called immediately,
    otherwise it will be called after this logging module has been initialized.

    This decorator is useful to register a function that creates a module level
    logger that is to be shared between functions in the module.

    Args:
        f (callable): A callable object that doesn't require any arguments
    """
    global _init_cbs
    if _top_logger is None:
        _init_cbs.append(f)
    else:
        f()
    return f


def initialize(top, cfg=None):
    """Initializes and Configures logging.

    Args:
        top (str): Name of the top logger

    Kwargs:
        cfg (str/obj): A filename, file-like object, dict.
                       If None, default configuration will be used.

    Exceptions:
        RuntimeError: init_logging() called multiple times
    """
    global _top_logger, _top_name
    if _top_logger is not None:
        raise RuntimeError("Logging has already been initialized with >{}<".format(_top_logger.name))

    _top_name   = top
    _top_logger = SimLog()

    _cfg(_top_name, cfg)

    global _init_cbs
    for cb in _init_cbs: cb()

    return _top_logger

def configure(cfg=None):
    """Configures logging

    Kwargs:
        cfg (str/obj): A filename, file-like object, dict.
                       If None, default configuration will be used.

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before re-configuring")

    _cfg(_top_name,cfg)

def _cfg(top, cfg=None):
    """Configures logging

    Args:
        top (str): Name of the top logger

    Kwargs:
        cfg (str/obj): A filename, file-like object, dict.
                       If None, default configuration will be used.
    """
    if cfg is None:
        if allow_ansi():
            formatter='sim_log_colour'
        else:
            formatter='sim_log'

        level = os.getenv("COCOTB_LOG_LEVEL", "INFO")

        cfg = StringIO(_DEFAULT_CONFIG.format(top=top, level=level, formatter=formatter))

    try:
        if not isinstance(cfg, dict):
            return _cfg_ini(cfg)
    except Exception as e:
        ini_err = str(e)

    try:
        return _cfg_dict(cfg)
    except Exception as e:
        dict_err = str(e)

    raise ValueError("The cfg object of type '{}' is of an incorrect format for logging configuration\n   ini: {}\n   dict: {}".format(type(cfg),ini_err, dict_err))

def _cfg_ini(cfg):
    logging.config.fileConfig(cfg)
    _notify_level_change()

def _cfg_dict(cfg):
    if isinstance(cfg, str):
        with open(cfg, 'r') as f:
            # Logging config files aren't that big.  Just read in everything.
            cfg = StringIO(f.read())

    if not isinstance(cfg, dict):
        try:
            import yaml as decoder
        except ImportError:
            import json as decoder
        cfg.seek(0) # Ensure starting at the beginning
        cfg = decoder.load(cfg)

    if hasattr(logging.config, 'dictConfig'):
        logging.config.dictConfig(cfg)
    else:
        # For older versions, support manual incremental configuration
        # Allows for setting (level, propagate) on loggers and (level,) on handlers.
        # No Structural changes.
        if 'version' not in cfg or cfg['version'] != 1:
            raise ValueError("The key 'version' must be specified and be equal to 1")

        if 'incremental' not in cfg or not cfg['incremental']:
            raise ValueError("The key 'incremental' must be specified and be equal to 1")

        handlers = cfg.get('handlers', {})
        for name in handlers:
            if name not in logging._handlers:
                raise ValueError('No handler found with '
                                 'name %r'  % name)
            else:
                try:
                    handler = logging._handlers[name]
                    handler_config = handlers[name]
                    level = handler_config.get('level', None)
                    if level:
                        handler.setLevel(logging._checkLevel(level))
                except Exception as e:
                    raise ValueError('Unable to configure handler '
                                     '%r: %s' % (name, e))
        loggers = cfg.get('loggers', {})
        for name in loggers:
            try:
                logger = logging.getLogger(name)
                propagate = cfg.get('propagate', None)
                if propagate is not None:
                    logger.propagate = propagate
                level = cfg.get('level', None)
                if level is not None:
                    logger.setLevel(logging._checkLevel(level))
            except Exception as e:
                raise ValueError('Unable to configure logger '
                                 '%r: %s' % (name, e))
        root = cfg.get('root', None)
        if root:
            try:
                logger = logging.getLogger()
                level = cfg.get('level', None)
                if level is not None:
                    logger.setLevel(logging._checkLevel(level))
            except Exception as e:
                raise ValueError('Unable to configure root '
                                 'logger: %s' % e)
    _notify_level_change()

def critical(msg, *args, **kwargs):
    """Log messages with severity 'CRITICAL' to the top logger.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                     All other kwargs are packed into a dictionary and added to extra
                     to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    _top_logger.critical(msg, *args, **kwargs)

def error(msg, *args, **kwargs):
    """Log messages with severity 'ERROR' to the top logger.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                     All other kwargs are packed into a dictionary and added to extra
                     to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    _top_logger.error(msg, *args, **kwargs)

def exception(msg, *args, **kwargs):
    """Log messages with severity 'ERROR' to the top logger with exception information.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        exc_info (boolean): Whether to include exception information.  Default is True
               **kwargs (): [extra, stack_info] are passed straight to the logger.
                            All other kwargs are packed into a dictionary and added to extra
                            to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    exc_info = kwargs.pop('exc_info', True)
    _top_logger.error(msg, *args, exc_info=exc_info, **kwargs)

def warning(msg, *args, **kwargs):
    """Log messages with severity 'WARNING' to the top logger.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                     All other kwargs are packed into a dictionary and added to extra
                     to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    _top_logger.warning(msg, *args, **kwargs)

def info(msg, *args, **kwargs):
    """Log messages with severity 'INFO' to the top logger.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                     All other kwargs are packed into a dictionary and added to extra
                     to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    _top_logger.info(msg, *args, **kwargs)

def verbose(msg, *args, **kwargs):
    """Log messages with severity 'VERBOSE' to the top logger.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                     All other kwargs are packed into a dictionary and added to extra
                     to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    _top_logger.verbose(msg, *args, **kwargs)

def debug(msg, *args, **kwargs):
    """Log messages with severity 'DEBUG' to the top logger.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                     All other kwargs are packed into a dictionary and added to extra
                     to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    _top_logger.debug(msg, *args, **kwargs)

def diagnostic(msg, *args, **kwargs):
    """Log messages with severity 'DIAGNOSTIC' to the top logger.

    Args:
        msg (str): Message to send to the logger
         *args (): Arguments for the msg, i.e. msg % *args

    Kwargs:
        **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                     All other kwargs are packed into a dictionary and added to extra
                     to allow to be used in the formatting strings

    Exceptions:
        RuntimeError: init_logging() not called first
    """
    if _top_logger is None:
        raise RuntimeError("init_logging() must be called before attempting to log")
    _top_logger.diagnostic(msg, *args, **kwargs)


class SimLog(object):
    def __init__(self, name=None, ident=None, mod=None, cls=None):
        """Creates an instance of the Logger.

        The name of the logger will be app[.mod][.cls][.name][.0x{ident:x}] where 'app' is the
        name provided to init_logging()

        Kwargs:
             name (str): name for the logger
            ident (int): an identifier, i.e. id()
              mod (str): name of the module with the logger
                             For module level loggers, use __name__
                             For class level loggers, use self.__module__

              cls (str): name of the class with the logger, use self.__class__.__name__

        Exceptions:
            RuntimeError: init_logging() not called first
        """
        if _top_name is None:
            raise RuntimeError("init_logging() must be called before creating an instance of {}".format(self.__class__.__name__))

        self._ident = ident
        self._name  = name

        # For Backwards compatibility
        if name is not None and name.startswith(_top_name):
            _name = [name]
        else:
            _name = [_top_name]
            if mod is not None:
                _name.append(mod)
            if cls is not None:
                _name.append(cls)
            if name is not None:
                _name.append(name)

        _log = '.'.join(_name)
        if ident is not None:
            self._log_name = '{}.0x{:x}'.format(_log,ident)
        else:
            self._log_name = _log
        self.logger = logging.getLogger(_log)

    def setLevel(self, level):
        self.logger.setLevel(level)
        _notify_level_change()

    def findCaller(self, stack_info=False):
        frame = inspect.stack()[3]
        info  = inspect.getframeinfo(frame[0])

        if info.filename == __file__:
            frame = inspect.stack()[4]
            info  = inspect.getframeinfo(frame[0])

        sinfo = None
        if stack_info:
            sio = StringIO()
            sio.write('Stack (most recent call last):\n')
            traceback.print_stack(frame[0], file=sio)
            sinfo = sio.getvalue()
            if sinfo[-1] == '\n':
                sinfo = sinfo[:-1]
            sio.close()

        return (info.filename, info.lineno, info.function, sinfo)

    def critical(self, msg, *args, **kwargs):
        """Log messages with severity 'CRITICAL' to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(CRITICAL):
            self._log(CRITICAL, msg, args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Log messages with severity 'ERROR' to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(ERROR):
            self._log(ERROR, msg, args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """Log messages with severity 'ERROR' to the logger with exception information.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            exc_info (boolean): Whether to include exception information.  Default is True
                   **kwargs (): [extra, stack_info] are passed straight to the logger.
                                All other kwargs are packed into a dictionary and added to extra
                                to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(ERROR):
            exc_info = kwargs.pop('exc_info', True)
            self._log(ERROR, msg, args, exc_info=exc_info, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Log messages with severity 'WARNING' to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(WARNING):
            self._log(WARNING, msg, args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Log messages with severity 'INFO' to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(INFO):
            self._log(INFO, msg, args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        """Log messages with severity 'VERBOSE' to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """Log messages with severity 'DEBUG' to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(DEBUG):
            self._log(DEBUG, msg, args, **kwargs)

    def diagnostic(self, msg, *args, **kwargs):
        """Log messages with severity 'DIAGNOSTIC' to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings
        """
        if self.logger.isEnabledFor(DIAGNOSTIC):
            self._log(DIAGNOSTIC, msg, args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        """Log messages of any level to the logger.

        Args:
            msg (str): Message to send to the logger
             *args (): Arguments for the msg, i.e. msg % *args

        Kwargs:
            **kwargs (): [exc_info, extra, stack_info] are passed straight to the logger.
                         All other kwargs are packed into a dictionary and added to extra
                         to allow to be used in the formatting strings

        Exceptions:
            TypeError: level isn't an int
        """
        if not isinstance(level, int):
            raise TypeError("level must be an integer")
        if self.logger.isEnabledFor(level):
            self._log(level, msg, args, **kwargs)

    def _log(self, level, msg, args, **kwargs):
        exc_info   = kwargs.pop('exc_info', None)
        extra      = kwargs.pop('extra', None)
        stack_info = kwargs.pop('stack_info', False)

        if extra is not None:
            extra.update(kwargs)
        elif kwargs:
            extra = kwargs

        sinfo = None

        fn, lno, func, sinfo = self.findCaller(stack_info)

        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()

        record = self.makeRecord(self._log_name, level, fn, lno, msg, args,
                                 exc_info, func, extra, sinfo)
        self.logger.handle(record)

    def makeRecord(self, name, level, fn, lno, msg, args, exc_info,
                   func=None, extra=None, sinfo=None):
        rv = logging.LogRecord(name, level, fn, lno, msg, args, exc_info, func)
        rv.stack_info = sinfo
        if extra is not None:
            for key in extra:
                if (key in ["message", "asctime", "simtime"]) or (key in rv.__dict__):
                    raise KeyError("Attempt to overwrite %r in LogRecord" % key)
                rv.__dict__[key] = extra[key]
        return rv

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
            record = self.makeRecord(self._log_name,
                                     level,
                                     filename,
                                     lineno,
                                     msg,
                                     None,
                                     None,
                                     function)
            self.logger.handle(record)

    def __getattr__(self, attribute):
        """Forward any attribute accesses on to our wrapped logger object"""
        return getattr(self.logger, attribute)


class InvalidColumnFormat(Exception):
    """Exception used by the ColumnFormatter"""
    pass

class StrFormatStyle(object):
    default_format = '{message}'
    asctime_format = '{asctime}'
    asctime_search = '{asctime'
    simtime_search = '{simtime'

    def __init__(self, fmt):
        self._fmt = fmt or self.default_format

    def usesTime(self):
        return self._fmt.find(self.asctime_search) >= 0

    def usesSimTime(self):
        return self._fmt.find(self.simtime_search) >= 0

    def format(self, record):
        return self._fmt.format(**record.__dict__)

class ColumnFormatter(logging.Formatter):
    default_simtime_format = '{:>6.2f}ns'
    fmt_spec_re            = re.compile('((?P<fill>.)?(?P<align>[<>=^]))?(?P<sign>[+\- ])?(?P<alt_form>#)?(?P<zero_fill>0)?(?P<width>\d+)?(?P<comma>,)?(?P<precision>\.\d+)?(?P<type>[bcdeEfFgGnosxX%])?')
    fmt_simtime_re         = re.compile('(?P<spec>.*?)?(?P<resolution>fs|ps|ns|us|ms|sec)')

    def __init__(self, fmt=None, datefmt=None, style=None, simtimefmt=None, separator=' | ', divider_char='-', divider_len=120, header_char='-', header_len=120, columns=[], show_cols=None):
        """Logging formatter that formats fields in columns, ensuring the text does
        not exceed the column width through truncation.  Column formats must be
        specified in the string format style, e.g. {col:8s}

        All columns must have a fixed width with the exception of the last column
        which is defined by the 'fmt' argument.

        Multi-line messages will be properly padded to maintain the column structure

        Kwargs:
                     fmt (str): Fromat for the last column
                 datefmt (str): Format string for creating {asctime}
                   style (str): IGNORED (Required for supporting fileConfig
              simtimefmt (str): Format string for creating {simtime}
               separator (str): The string separating the columns
           divider_char (char): Character for the divider markers
             divider_len (int): Length of the divider markers
            header_char (char): Character for the divider markers
              header_len (int): Length of the divider markers
                columns (list): List of formats for persistent columns
              show_cols (list): List of columns to display (None means all, Empty only shows the message)

        Excetpions:
                      TypeError: 'columns' not a list
            InvalidColumnFormat: Issue processing the column format
        """
        if columns is not None and not isinstance(columns, list):
            raise TypeError("Argument 'columns' must be of type list.")

        self._style       = StrFormatStyle(fmt)
        self._fmt         = self._style._fmt
        self.datefmt      = datefmt
        self.simtimefmt   = simtimefmt or self.default_simtime_format
        self._usestime    = self._style.usesTime()
        self._usessimtime = self._style.usesSimTime()
        self._sep         = separator

        divider_len = int(divider_len)
        self._divider  = '{{message:{}^{}}}'.format(divider_char, divider_len)
        
        header_len = int(header_len)
        self._hdr_len  = header_len-6
        self._hdr_div  = header_char*header_len
        self._header   = '{} {{line:{}}} {}'.format(header_char*2, self._hdr_len, header_char*2)

        self._columns   = []

        for col_fmt in columns:
            col = {}
            _style = StrFormatStyle(col_fmt)
            self._usestime = self._usestime or _style.usesTime()
            self._usessimtime = self._usessimtime or _style.usesSimTime()
            col['style'] = _style
            col['fmt']   = _style._fmt
            parsed, _len = self._parse_fmt(col_fmt)
            col['len']   = _len
            col['parsed'] = parsed

            self._columns.append(col)

        self._show_cols = show_cols if show_cols is not None else [i for i in range(len(self._columns))]

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
        s = []

        show_cols = getattr(record, 'show_cols', self._show_cols)

        if not getattr(record, 'suppress', False):
            for col in [c for i, c in enumerate(self._columns) if i in show_cols]:
                try:
                    c = self._trunc(col['style'].format(record),col['len'])
                    s.append("{}{}".format(c,self._sep))
                except KeyError:
                    s.append("{}{}".format(' '*col['len'],self._sep))

        msg = super(ColumnFormatter, self).formatMessage(record)

        s.append(self._fmt_multi_line_msg(msg,record))

        return ''.join(s)

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
            raise ValueError('Invalid SimTime Format String: {}'.format(fmt))

        res     = parsed.groupdict()['resolution']
        simtime = get_sim_time(res)

        return fmt.format(simtime)

    def format(self, record):
        """Returns a string of the formatted message with all of the columns,
        including the exception information and the stack information.

        Args:
            record (obj): Container with all the parameters for formatting
        """
        show_cols = getattr(record, 'show_cols', self._show_cols)

        record.pad = ""
        for col in [c for i, c in enumerate(self._columns) if i in show_cols]:
            record.pad += "{}{}".format(' '*col['len'],self._sep)

        record.message = record.getMessage()

        if getattr(record, 'header', False):
            s = self.formatHeader(record)
        elif getattr(record, 'divider', False):
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
            return '..{0}'.format(s[(max_len - 2) * -1:])
        return s

    def _fmt_multi_line_msg(self,msg,record,pad_first_line=False):
        """Returns a formatted string that has been properly padded on each line.

        Args:
                           msg (str): The string to process
                        record (obj): The message record
            pad_first_line (boolean): Indicates whether padding should be applied
                                      to the first line
        """
        if not getattr(record, 'suppress', False):
            pad = '\n{0}'.format(record.pad)

            s = '{0}{1}'.format(pad[1:] if pad_first_line else '', pad.join(msg.split('\n')))
        else:
            s = msg
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

    def __init__(self, fmt=None, datefmt=None, style=None, simtimefmt=None, separator=' | ', divider_char='-', divider_len=120, header_char='-', header_len=120, show_cols=None):
        ColumnFormatter.__init__(self,
                                 fmt=fmt,
                                 datefmt=datefmt,
                                 style=style,
                                 simtimefmt=simtimefmt,
                                 separator=separator,
                                 divider_char=divider_char,
                                 divider_len=divider_len,
                                 header_char=header_char,
                                 header_len=header_len,
                                 columns=['{simtime:>14s}', '{levelname:<10s}', '{name:<35}', '{filename:>20}:{lineno:<4}', '{funcName:<31}'],
                                 show_cols=show_cols)

class SimColourLogFormatter(SimLogFormatter):

    """Log formatter to provide consistent log message handling."""
    loglevel2colour = {
        DIAGNOSTIC:       ANSI.COLOR_DEFAULT   + "%s" + ANSI.COLOR_DEFAULT,
        DEBUG     :       ANSI.COLOR_DEFAULT   + "%s" + ANSI.COLOR_DEFAULT,
        VERBOSE   :       ANSI.COLOR_DEFAULT   + "%s" + ANSI.COLOR_DEFAULT,
        INFO      :       ANSI.COLOR_INFO      + "%s" + ANSI.COLOR_DEFAULT,
        WARNING   :       ANSI.COLOR_WARNING   + "%s" + ANSI.COLOR_DEFAULT,
        ERROR     :       ANSI.COLOR_ERROR     + "%s" + ANSI.COLOR_DEFAULT,
        CRITICAL  :       ANSI.COLOR_CRITICAL  + "%s" + ANSI.COLOR_DEFAULT}

    def __init__(self, fmt=None, datefmt=None, style=None, simtimefmt=None, separator=' | ', divider_char='-', divider_len=120, header_char='-', header_len=120, show_cols=None):
        SimLogFormatter.__init__(self,
                                 fmt=fmt,
                                 datefmt=datefmt,
                                 simtimefmt=simtimefmt,
                                 separator=separator,
                                 divider_char=divider_char,
                                 divider_len=divider_len,
                                 header_char=header_char,
                                 header_len=header_len,
                                 show_cols=show_cols)

    def _formatColumn(self, col, record):
        """Returns a string of the formated column.

        Args:
              col (dict): Column information dictionary
            record (obj): Container with all the parameters for formatting
        """
        s = SimLogFormatter._formatColumn(self, col=col, record=record)

        if id(col) == id(self._columns[1]):
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

