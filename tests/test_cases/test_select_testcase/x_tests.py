import cocotb

@cocotb.test()
async def x_test(dut):
  dut._log.info("x_test")
