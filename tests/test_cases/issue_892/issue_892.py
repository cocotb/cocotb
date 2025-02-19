import cocotb
from cocotb.result import TestSuccess
from cocotb.triggers import Timer


async def raise_test_success():
    await Timer(1, unit="ns")
    raise TestSuccess("TestSuccess")


@cocotb.test()
async def error_test(dut):
    cocotb.start_soon(raise_test_success())
    await Timer(10, unit="ns")
