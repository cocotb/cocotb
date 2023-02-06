import cocotb


@cocotb.test()
async def issue_3239(dut):
    dut.t.a.value = 0
