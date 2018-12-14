from cocotb.log import SimLog, register_initialize_cb

log = None

@register_initialize_cb
def _create_module_logger():
    global log
    log = SimLog(mod=__name__)

class Dummy(object):
    def __init__(self, name):
        self.name = name
        self.log = SimLog(mod=self.__module__, cls=self.__class__.__name__, name=name)

    def cls_print(self):
        self.log.diagnostic("{} is logging DIAGNOSTIC".format(self.log.name))
        self.log.debug("{} is logging DEBUG".format(self.log.name))
        self.log.verbose("{} is logging VERBOSE".format(self.log.name))
        self.log.info("{} is logging INFO".format(self.log.name))
        self.log.warning("{} is logging WARNING".format(self.log.name))
        self.log.error("{} is logging ERROR".format(self.log.name))
        self.log.critical("{} is logging CRITICAL".format(self.log.name))

def fun_print():
    log.diagnostic("{} is logging DIAGNOSTIC".format(log.name))
    log.debug("{} is logging DEBUG".format(log.name))
    log.verbose("{} is logging VERBOSE".format(log.name))
    log.info("{} is logging INFO".format(log.name))
    log.warning("{} is logging WARNING".format(log.name))
    log.error("{} is logging ERROR".format(log.name))
    log.critical("{} is logging CRITICAL".format(log.name))

