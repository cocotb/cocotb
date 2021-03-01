import cocotb

@cocotb.test()
async def y_test(dut):
    dut._log.info("y_test")
