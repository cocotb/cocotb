import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestSuccess

@cocotb.coroutine
def raise_test_success():
    yield Timer(1, units='ns')
    raise TestSuccess("TestSuccess")

@cocotb.test()
def error_test(dut):
    cocotb.fork(raise_test_success())
    yield Timer(10, units='ns')
