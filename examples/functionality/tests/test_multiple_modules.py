import cocotb
from cocotb.triggers import Timer, Join

@cocotb.test(expect_fail=False)
def simple_test(dut):
    """Simple test in another module"""
    yield Timer(10000)


