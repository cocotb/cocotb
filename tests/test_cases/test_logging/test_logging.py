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


