
import cocotb
from cocotb.triggers import Timer

@cocotb.test()
def discover_module_values(dut):
    """Discover everything in the dut"""
    yield Timer(0)
    for thing in dut:
        thing.log.info("Found something: %s" % thing.fullname)

@cocotb.test(expect_fail=True)
def discover_value_not_in_dut(dut):
    """Try and get a value from the DUT that is not there"""
    yield Timer(0)
    fake_signal = dut.fake_signal
