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


@cocotb.test(expect_fail=False)
def test_function_reentrant_clock(dut):
    """Test yielding a reentrant clock"""
    clock = dut.clk
    timer = Timer(100)
    for i in range(10):
        clock <= 0
        yield timer
        clock <= 1
        yield timer


@cocotb.test(expect_fail=False)
def test_burst_read(dut):
    """ Testing burst read """
    # Launch clock
    dut.reset = 1
    clk_gen = cocotb.fork(Clock(dut.clk, 10).start())

    memdict = {}
    avl32 = AvalonMemory(dut, "master", dut.clk)
    yield Timer(10)
    dut.reset = 0
    dut.control_read_base = 0
    dut.control_read_length = 32
    dut.control_fixed_location = 0
    dut.control_go = 0
    dut.master_waitrequest = 0
    yield Timer(100)
    dut.control_go = 1
    yield Timer(1000)

