
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
def discover_module_values(dut):
    """Discover everything in the dut"""
    yield Timer(0)
    for thing in dut:
        thing.log.info("Found something: %s" % thing.fullname)

