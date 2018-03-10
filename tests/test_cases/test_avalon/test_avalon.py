#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''
import logging

"""
A set of tests that demonstrate cocotb functionality

Also used a regression test of cocotb capabilities
"""

import cocotb
from cocotb.drivers.avalon import AvalonMemory
from cocotb.triggers import (Timer, Join, RisingEdge, FallingEdge, Edge,
                             ReadOnly, ReadWrite)
from cocotb.clock import Clock
from cocotb.result import ReturnValue, TestFailure, TestError, TestSuccess



class BurstAvlReadTest(object):
    """ class to test avalon burst """

    def __init__(self, dut, avlproperties={}):
        self.dut = dut
        # Launch clock
        dut.reset = 1
        clk_gen = cocotb.fork(Clock(dut.clk, 10).start())

        # Bytes aligned memory
        self.memdict = {value: value for value in range(0x1000)}

        self.avl32 = AvalonMemory(dut, "master", dut.clk,
                                  memory=self.memdict,
                                  readlatency_min=0,
                                  avl_properties=avlproperties)
    @cocotb.coroutine
    def init_sig(self, burstcount_w, address):
        """ initialize all signals"""
        yield Timer(10)
        self.dut.reset = 0
        self.dut.user_read_buffer = 0
        self.dut.control_read_base = address
        self.dut.control_read_length = burstcount_w*4
        self.dut.control_fixed_location = 0
        self.dut.control_go = 0
        self.dut.master_waitrequest = 0

@cocotb.test(expect_fail=False)
def test_burst_read(dut):
    """ Testing burst read """
    wordburstcount = 16
    address = 10*wordburstcount

    bart = BurstAvlReadTest(dut, {"readLatency": 10})
    yield bart.init_sig(wordburstcount, address)
    yield Timer(100)
    # Begin master burst read
    dut.control_go = 1
    yield Timer(10)
    dut.control_go = 0
    yield Timer(200)

    # read back values
    dut.user_read_buffer = 1
    yield RisingEdge(dut.clk)
    read_mem = {}
    databuswidthB = len(dut.master_byteenable)
    burst = 0
    while dut.user_data_available == 1:
        yield RisingEdge(dut.clk)
        value = dut.user_buffer_data.value
        for i in range(databuswidthB):
            read_mem[address + burst*databuswidthB + i] =\
                    (value >> i*8)& 0xFF
        burst += 1

    dut.user_read_buffer = 0
    yield RisingEdge(dut.clk)

    print(str(read_mem))
    print(str(len(read_mem)) + " 8bits values read")

    # checking values read
    for key, value in read_mem.items():
        memdictvalue = bart.memdict.get(key, None)
        if memdictvalue != value:
            if memdictvalue is None:
                memdictvalue = "Error"
            else:
                memdictvalue = hex(memdictvalue)
            raise TestFailure("Wrong value read in memory :" +
                              " read_mem[" + hex(key) + "] = " +
                              hex(value) + " must be " +
                              memdictvalue)

    yield Timer(10)
    dut.user_read_buffer = 0
    yield Timer(10)
