import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestSuccess


async def raise_test_success():
    await Timer(1, units='ns')
    raise TestSuccess("TestSuccess")


@cocotb.test()
async def error_test(dut):
    cocotb.start_soon(raise_test_success())
    await Timer(10, units='ns')
