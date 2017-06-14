#! /usr/bin/python3
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------------
# Author:   Fabien Marteau <fabien.marteau@armadeus.com>
# Created:  28/04/2017
#-----------------------------------------------------------------------------
#  Copyright (2017)  Armadeus Systems
#-----------------------------------------------------------------------------
""" test_axi_pattern_tester

* Use AXI_update cocotb branch from Martoni github to simulate it :
    $ git clone https://github.com/Martoni/cocotb.git
    $ cd cocotb;git checkout AXI_update
* Use master git of ghdl for VHDL simulation :
    $ git clone https://github.com/tgingold/ghdl.git
    $ cd ghdl
    $ ./configure
    $ make
    $ sudo make install

"""

import sys

import logging
import array

import cocotb
from cocotb.triggers import Timer
from cocotb.result import raise_error, TestFailure
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.drivers.amba import AXI4LiteMaster
from cocotb.drivers.amba import AXI4Slave
from cocotb.drivers.amba import AXIProtocolError

PS = 1
NS = 1000*PS
US = 1000*NS
MS = 1000*US

# 200Mhz
HALF_CLK = 2500*PS

SKIP_LIST = [
#    'axi4lite_slave_test',
#    'axi4_master_test'
]

def skip_test(test_name):
    if test_name in SKIP_LIST:
        return True
    return False

class AxiPatternTest(object):
    """ class to test axi pattern test """

    def __init__(self, dut):
        self.dut = dut

    def initialization(self):
        self.dut._log.info("Running test!")
        self.clk_per = 2*HALF_CLK
        self.dut._log.info("Period clock value : {} ps"
                .format(self.clk_per))
        self.s00_clock_thread = cocotb.fork(Clock(self.dut.s00_axi_aclk,
                                                  self.clk_per).start())
        self.m00_clock_thread = cocotb.fork(Clock(self.dut.m00_axi_aclk,
                                                  self.clk_per).start())

    @cocotb.coroutine
    def slave_init(self):
        self.memory = array.array('B','')
        self.m00_slave = AXI4Slave(self.dut, "m00_axi",
                                   self.dut.m00_axi_aclk,
                                   self.memory)
        self.dut.s00_axi_aresetn = 0
        self.dut.m00_axi_aresetn = 0
        self.dut.m00_axi_init_axi_txn = 0
        yield self.reset_dut([self.dut.s00_axi_aresetn,
                              self.dut.m00_axi_aresetn], 9*NS)

    @cocotb.coroutine
    def master_init(self):
        self.s00_masterlite = AXI4LiteMaster(self.dut,
                                             "s00_axi",
                                             self.dut.s00_axi_aclk)
        yield self.reset_dut([self.dut.s00_axi_aresetn,
                              self.dut.m00_axi_aresetn], 9*NS)

    @cocotb.coroutine
    def master_launch_write(self):
        self.dut.m00_axi_init_axi_txn = 1
        yield RisingEdge(self.dut.m00_axi_aclk)
        yield RisingEdge(self.dut.m00_axi_aclk)
        self.dut.m00_axi_init_axi_txn = 0

    def print_master_generics(self):
        self.dut._log.info("C_M00_AXI_BURST_LEN 0x{:x}".format(
            int(self.dut.c_m00_axi_burst_len)))
        self.dut._log.info("C_M00_AXI_ID_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_id_width)))
        self.dut._log.info("C_M00_AXI_ADDR_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_addr_width)))
        self.dut._log.info("C_M00_AXI_DATA_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_data_width)))
        self.dut._log.info("C_M00_AXI_AWUSER_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_awuser_width)))
        self.dut._log.info("C_M00_AXI_ARUSER_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_aruser_width)))
        self.dut._log.info("C_M00_AXI_WUSER_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_wuser_width)))
        self.dut._log.info("C_M00_AXI_RUSER_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_ruser_width)))
        self.dut._log.info("C_M00_AXI_BUSER_WIDTH 0x{:x}".format(
            int(self.dut.c_m00_axi_buser_width)))

    @cocotb.coroutine
    def reset_dut(self, resetlist, duration, negate=True):
        if negate:
            for rst in resetlist:
                rst <= 0
        else:
            for rst in resetlist:
                rst <= 1
        yield Timer(duration)
        if negate:
            for rst in resetlist:
                rst <= 1
        else:
            for rst in resetlist:
                rst <= 0
        resetlist[0]._log.info("Reset complete")

@cocotb.test(skip=skip_test('axi4lite_slave_test'))
def axi4lite_slave_test(dut):
    """
        test axi4 slave
    """
    cocotblog = logging.getLogger("cocotb")
    dutest = AxiPatternTest(dut)
    dutest.initialization()

    yield dutest.master_init()

    yield Timer(20*NS)

    writevalues = [0xCACABEBE, 0xDEADBEEF, 0x12345678, 0x98765432]
    readvalues = [0, 0, 0, 0]

    dut.log.info("Write values")
    addr = 0x00
    for value in writevalues:
        yield dutest.s00_masterlite.write(addr<<2, value)
        addr = addr + 1
        yield Timer(2*NS)

    dut.log.info("Read back values")
    addr = 0x00
    addrlst = []
    for value in writevalues:
        readvalues[addr] = yield dutest.s00_masterlite.read(addr<<2)
        addrlst.append(addr)
        addr = addr + 1
        yield Timer(2*NS)

    yield Timer(20*NS)
    for readvalue, writevalue, addr  in zip(readvalues, writevalues, addrlst):
        if writevalue != int(readvalue):
            raise TestFailure("Error  @0x{:08X} wrote 0x{:08X}  read 0x{:08x}"
                                .format(addr<<2, writevalue, int(readvalue)))
        dut.log.info("@0x{:04X} wrote 0x{:08X}  read 0x{:08X}"
                                .format(addr<<2, writevalue, int(readvalue)))
    dut.log.info("Test done")

@cocotb.test(skip=skip_test('axi4_master_test'))
def axi4_master_test(dut):
    """
        test axi4 master
    """
    cocotblog = logging.getLogger("cocotb")
    dutest = AxiPatternTest(dut)
    dutest.initialization()
    dutest.print_master_generics()
    yield dutest.slave_init()
    dut.log.info("master initialized")
    yield dutest.master_launch_write()
    
    timeout_15us = Timer(15*US)
    rtxn_done = RisingEdge(dut.m00_axi_txn_done)
    end_of_test = yield [timeout_15us, rtxn_done]
    if end_of_test == rtxn_done:
        if dut.m00_axi_error.value != 0:
            raise TestFailure("Values comparing error")
        else:
            yield Timer(1*US)
            dut.log.info("Test done")
    else:
        raise TestFailure("m00_axi_txn_done not raised, failed to transmit")
