# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
A set of tests that demonstrate cocotb functionality

Also used as regression test of cocotb capabilities
"""

import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.clock import Clock
from cocotb.result import TestFailure

from cocotb_bus.drivers.avalon import AvalonMemory


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

    async def init_sig(self, burstcount_w, address):
        """ Initialize all signals """
        await Timer(1, "ns")
        self.dut.reset = 0
        self.dut.user_read_buffer = 0
        self.dut.control_read_base = address
        self.dut.control_read_length = burstcount_w*4
        self.dut.control_fixed_location = 0
        self.dut.control_go = 0
        self.dut.master_waitrequest = 0


@cocotb.test()
async def test_burst_read(dut):
    """ Testing burst read """
    wordburstcount = 16
    address = 10*wordburstcount

    bart = BurstAvlReadTest(dut, {"readLatency": 10})
    await bart.init_sig(wordburstcount, address)
    await Timer(100, "ns")
    # Begin master burst read
    dut.control_go = 1
    await Timer(10, "ns")
    dut.control_go = 0
    await Timer(200, "ns")

    # read back values
    dut.user_read_buffer = 1
    await RisingEdge(dut.clk)
    read_mem = {}
    databuswidthB = len(dut.master_byteenable)
    burst = 0
    while dut.user_data_available == 1:
        await RisingEdge(dut.clk)
        value = dut.user_buffer_data.value
        for i in range(databuswidthB):
            read_mem[address + burst*databuswidthB + i] = \
                (value >> i*8)& 0xFF
        burst += 1

    dut.user_read_buffer = 0
    await RisingEdge(dut.clk)

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

    await Timer(1, "ns")
    dut.user_read_buffer = 0
    await Timer(1, "ns")
