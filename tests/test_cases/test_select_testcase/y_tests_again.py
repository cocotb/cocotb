import cocotb


@cocotb.test()
async def y_test(dut):
    dut._log.error("y_test_again")
    raise Exception("Only the first test that matches TESTCASE should be run")
