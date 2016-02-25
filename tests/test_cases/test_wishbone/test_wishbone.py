import logging

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.drivers.wishbone import WishboneMaster

class GPIOTB(object):

    def __init__(self, dut, debug=False):
        self.dut = dut
        self.log = logging.getLogger("cocotb.gpiotb")

        # 
_signals = ["cyc", "stb", "we", "sel", "adr", "datwr", "datrd", "ack"]


@cocotb.test()
def simple_wb_test(dut):
    cocotb.fork(Clock(dut.wb_clk_i, 1000).start())

    for i in range(100):
        yield RisingEdge(dut.wb_clk_i)
