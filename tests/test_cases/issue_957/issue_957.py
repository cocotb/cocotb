import cocotb
from cocotb.triggers import Timer, RisingEdge, First


async def wait_edge(dut):
    # this trigger never fires
    await First(RisingEdge(dut.stream_out_ready))


@cocotb.test()
async def test1(dut):
    cocotb.start_soon(wait_edge(dut))
    await Timer(10, 'ns')


test2 = test1
