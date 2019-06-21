import cocotb
from cocotb.triggers import Timer, RisingEdge, First

@cocotb.coroutine
def wait_edge(dut):
    # this trigger never fires
    yield First(
        RisingEdge(dut.and_output)
    )

@cocotb.test()
def test1(dut):
    cocotb.fork(wait_edge(dut))

    yield Timer(1000)

test2 = test1
