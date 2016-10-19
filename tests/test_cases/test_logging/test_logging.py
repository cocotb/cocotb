import io
import os.path
import logging.config as py_log_cfg

import cocotb
import cocotb.log as logging
from cocotb.triggers import Timer

import dummy

obj1 = dummy.Dummy('abc')
obj2 = dummy.Dummy('def')

@cocotb.coroutine
def log(hdr):
    global obj1, obj2

    yield Timer(1, units='ns')

    logging.critical(hdr,header=True)
    logging.deep_debug('Top Logger is DEEP_DEBUG')
    logging.debug('Top Logger is DEBUG')
    logging.info('Top Logger is INFO')
    logging.warning('Top Logger is WARNING')
    logging.error('Top Logger is ERROR')
    logging.critical('Top Logger is CRITICAL')
    dummy.fun_print()
    obj1.cls_print()
    obj2.cls_print()
    logging.critical('',divider=True)

@cocotb.test()
def t01_basic_logging(dut):
    s  = "Using the default configuration:\n"
    s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
    s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "      Class Logger -  Dummy: Log Level inherited from Module Logger, i.e. INFO and above\n"
    s += "   Instance Logger -    abc: Log Level inherited from Class Logger, i.e. INFO and above\n"
    s += "   Instance Logger -    def: Log Level inherited from Class Logger, i.e. INFO and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

    # Directly access a Logger to set the Level
    logging.SimLog(mod='dummy', cls='Dummy').setLevel(logging.DEEP_DEBUG)

    s  = "Update the class log level to DEEP_DEBUG:\n"
    s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
    s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "      Class Logger -  Dummy: Will log all messages of DEEP_DEBUG and above\n"
    s += "   Instance Logger -    abc: Log Level inherited from Class Logger, i.e. DEEP_DEBUG and above\n"
    s += "   Instance Logger -    def: Log Level inherited from Class Logger, i.e. DEEP_DEBUG and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

    # Directly access a Logger to set the Level
    logging.SimLog(mod='dummy', cls='Dummy').setLevel(logging.NOTSET)
    logging.SimLog(mod='dummy').setLevel(logging.ERROR)
    logging.SimLog(mod='dummy', cls='Dummy', name='abc').setLevel(logging.CRITICAL)

    s  = "Clear the class level, Set Module Level to Error, and Instance 'abc' to CRITICAL:\n"
    s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
    s += "     Module Logger -  dummy: Will log all messages of ERROR and above\n"
    s += "      Class Logger -  Dummy: Log Level inherited from Module Logger, i.e. ERROR and above\n"
    s += "   Instance Logger -    abc: Will log all messages of CRITICAL and above\n"
    s += "   Instance Logger -    def: Log Level inherited from Class Logger, i.e. ERROR and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

    logging.info("Demonstrate a multi-line message...",header=True)
    logging.critical('Top Logger logged a multi-line CRITICAL\nLINE 2\nLINE 3')
    logging.info('EXAMPLE OF DIVIDER WITH TEXT',divider=True)

    logging.info("Demonstrate a multi-line message with no columns...",header=True)
    logging.critical('Top Logger logged a multi-line CRITICAL\nLINE 2\nLINE 3', suppress=True)
    logging.info('',divider=True)

@cocotb.test()
def t02_dflt_config(dut):
    # Configure with the defult configuration
    logging.configure()

    s  = "Using the default configuration:\n"
    s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
    s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "      Class Logger -  Dummy: Log Level inherited from Module Logger, i.e. INFO and above\n"
    s += "   Instance Logger -    abc: Log Level inherited from Class Logger, i.e. INFO and above\n"
    s += "   Instance Logger -    def: Log Level inherited from Class Logger, i.e. INFO and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

@cocotb.test()
def t03_helper_function(dut):
    # Configure with the defult configuration
    current = cocotb.cocotbLogGetLevel()
    cocotb.cocotbLogSetLevel(logging.DEEP_DEBUG)

    s  = "Set the top logger level to DEEP_DEBUG:\n"
    s += "        Top Logger - cocotb: Will log all messages of DEEP_DEBUG and above\n"
    s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. DEEP_DEBUG and above\n"
    s += "      Class Logger -  Dummy: Log Level inherited from Module Logger, i.e. DEEP_DEBUG and above\n"
    s += "   Instance Logger -    abc: Log Level inherited from Class Logger, i.e. DEEP_DEBUG and above\n"
    s += "   Instance Logger -    def: Log Level inherited from Class Logger, i.e. DEEP_DEBUG and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

    cocotb.cocotbLogSetLevel(current)

@cocotb.test()
def t04_optional_columns(dut):
    logging.info("Force Optional Columns to be shown", include_optional=True)
    logging.info("Force Optional Columns to be hidden", include_optional=False)

    yield Timer(1, units='ns')

@cocotb.test()
def t05_incremental_cfg(dut):
    cfg = {
        'version':1,
        'incremental':True,
        'loggers': {
            'cocotb.dummy.Dummy':     { 'level': logging.ERROR },
            'cocotb.dummy.Dummy.def': { 'level': logging.DEBUG }
        }
    }
    logging.configure(cfg)

    s  = "Update configuration with incremental update:\n"
    s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
    s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "      Class Logger -  Dummy: Will log all messages of ERROR and above\n"
    s += "   Instance Logger -    abc: Log Level inherited from Class Logger, i.e. ERROR and above\n"
    s += "   Instance Logger -    def: Will log all messages of DEBUG and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

    logging.configure()

@cocotb.test()
def t06_file_cfg(dut):
    loc = os.path.dirname(__file__)
    logging.configure(os.path.join(loc,'log_cfg.ini'))

    s  = "Using the configuration in log_cfg.ini:\n"
    s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
    s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "      Class Logger -  Dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "   Instance Logger -    abc: Will log all messages of DEEP_DEBUG and above\n"
    s += "   Instance Logger -    def: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

    if hasattr(py_log_cfg, 'dictConfig'):
        logging.configure(os.path.join(loc,'log_cfg.json'))

        s  = "Using the configuration in log_cfg.json:\n"
        s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
        s += "     Module Logger -  dummy: Will log all messages of CRITICAL and above\n"
        s += "      Class Logger -  Dummy: Log Level inherited from Module Logger, i.e. CRITICAL and above\n"
        s += "   Instance Logger -    abc: Log Level inherited from Module Logger, i.e. CRITICAL and above\n"
        s += "   Instance Logger -    def: Log Level inherited from Module Logger, i.e. CRITICAL and above\n"
        s += "\n"
        s += "                    console: Will display any message actually logged\n"
        s += "                       file: N/A"

        yield log(s)

        try:
            import yaml
            logging.configure(os.path.join(loc,'log_cfg.yaml'))

            s  = "Using the configuration in log_cfg.yaml:\n"
            s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
            s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
            s += "      Class Logger -  Dummy: Will log all messages of DEEP_DEBUG and above\n"
            s += "   Instance Logger -    abc: Log Level inherited from Class Logger, i.e. DEEP_DEBUG and above\n"
            s += "   Instance Logger -    def: Log Level inherited from Class Logger, i.e. DEEP_DEBUG and above\n"
            s += "\n"
            s += "                    console: Will display any message of WARNING or higher\n"
            s += "                       file: N/A"

            yield log(s)
        except ImportError:
            pass


    logging.configure()

@cocotb.test()
def t07_stringio_cfg(dut):
    cfg = \
'''
[loggers]
keys=root,top,inst1

[handlers]
keys=console

[formatters]
keys=sim_log

[logger_root]
level=WARNING
handlers=

[logger_top]
level=INFO
handlers=console
propagate=0
qualname=cocotb

[logger_inst1]
level=CRITICAL
handlers=console
qualname=cocotb.dummy.Dummy.abc

[handler_console]
class=StreamHandler
level=NOTSET
formatter=sim_log
args=(sys.stdout,)

[formatter_sim_log]
class=cocotb.log.SimLogFormatter
'''
    logging.configure(io.StringIO(cfg))

    s  = "Using the INI configuration:\n"
    s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
    s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "      Class Logger -  Dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "   Instance Logger -    abc: Will log all messages of CRITICAL and above\n"
    s += "   Instance Logger -    def: Log Level inherited from Top Logger, i.e. INFO and above\n"
    s += "\n"
    s += "                    console: Will display any message actually logged\n"
    s += "                       file: N/A"

    yield log(s)

    if hasattr(py_log_cfg, 'dictConfig'):
        cfg = \
'''
{
    "version": 1,
    "incremental": false,
    "formatters": {
        "console_formatter": {
            "()": "cocotb.log.SimColourLogFormatter",
            "simtimefmt": "{:>6.3f}us"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console_formatter",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        "cocotb": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": false
        },
        "cocotb.dummy": {
            "level": "ERROR"
        }
    }
}
'''
        logging.configure(io.StringIO(cfg))

        s  = "Using the JSON configuration:\n"
        s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
        s += "     Module Logger -  dummy: Will log all messages of ERROR and above\n"
        s += "      Class Logger -  Dummy: Log Level inherited from Module Logger, i.e. ERROR and above\n"
        s += "   Instance Logger -    abc: Log Level inherited from Module Logger, i.e. ERROR and above\n"
        s += "   Instance Logger -    def: Log Level inherited from Module Logger, i.e. ERROR and above\n"
        s += "\n"
        s += "                    console: Will display any message actually logged\n"
        s += "                       file: N/A"

        yield log(s)

        try:
            import yaml
            cfg = \
'''
version: 1
incremental: False

formatters:
    console_formatter:
        (): cocotb.log.SimLogFormatter
        separator: " && "

handlers:
    console:
        class: logging.StreamHandler
        formatter: console_formatter
        level: ERROR
        stream: "ext://sys.stdout"

loggers:
    cocotb:
        level: INFO
        propagate: False
        handlers:
            - console
'''
            logging.configure(io.StringIO(cfg))

            s  = "Using the YAML configuration:\n"
            s += "        Top Logger - cocotb: Will log all messages of INFO and above\n"
            s += "     Module Logger -  dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
            s += "      Class Logger -  Dummy: Log Level inherited from Top Logger, i.e. INFO and above\n"
            s += "   Instance Logger -    abc: Log Level inherited from Top Logger, i.e. INFO and above\n"
            s += "   Instance Logger -    def: Log Level inherited from Top Logger, i.e. INFO and above\n"
            s += "\n"
            s += "                    console: Will display any message of ERROR or higher\n"
            s += "                       file: N/A"

            yield log(s)
        except ImportError:
            pass

    logging.configure()

