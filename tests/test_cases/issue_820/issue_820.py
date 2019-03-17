# A set of regression tests for open issues

import cocotb
import logging
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.result import TestFailure

@cocotb.test()
def issue_820(dut):
    tlog = logging.getLogger("cocotb.test")

    cocotb.fork(Clock(dut.clk, 2500).start())

    dut.rst <= 1
    dut.enable <= 0
    yield Timer(10000)
    dut.rst <= 0
    yield Timer(10000)
    dut.enable <= 1

    while dut.done != 15:
        yield RisingEdge(dut.clk)
        tlog.info("Counter[3].cnt = %d", int(dut.counters.install_gen.cntr[3].c_i.cnt))


    tlog.info("DONE!!!!")
