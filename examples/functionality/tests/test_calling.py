#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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

"""
A set of tests that demonstrate cocotb functionality

Also used a regression test of cocotb capabilities
"""

import threading
import time
import cocotb
from cocotb.triggers import Timer, Join, RisingEdge, ReadOnly

signal = None

# Tests relating to calling convention and operation

def create_thread():
    new_thread = threading.Thread(group=None, target=blocking_function, name="Test_thread", args=(), kwargs={})
    new_thread.start()

@cocotb.function
def blocking_function():
    global signal
    stime = 2
    print("Blocking for %d seconds then asserting clock" % stime)
    time.sleep(stime)
    signal <= 1
    print("Block finished")

clock_count = 0

@cocotb.coroutine
def clock_gen(clock):
    """Drive the clock signal"""
    global clock_count

    for i in range(10000):
        clock <= 0
        yield Timer(1000)
        clock <= 1
        yield Timer(1000)
        clock_count += 1

    clock.log.warning("Clock generator finished!")

signal_count = 0

@cocotb.coroutine
def signal_monitor(signal):
    """Check that the clock is moving and increment
    a counter
    """
    global signal_count

    yield RisingEdge(signal)
    signal_count += 1

    print("Clock mon exiting")


@cocotb.test(expect_fail=False)
def test_callable(dut):
    """Test ability to call a blocking function that will block but allow other coroutines to continue

    The test creates another thread that will block for a period of time. This would normally
    mean that the simulator could not progress since control would not pass back to the simulator

    In this test the clock driver should continue to be able to toggle pins
    we monitor this as well and count that the number of observed transitions matches the number of sets
    """
    global clock_count
    global signal
    signal = dut.stream_in_valid
    signal_mon = cocotb.scheduler.add(signal_monitor(signal))
    clk_gen = cocotb.scheduler.add(clock_gen(dut.clk))
    create_thread()
    #blocking_function()
    yield Timer(1000)
    yield Join(signal_mon)
    clk_gen.kill()
    print("Have had %d transitions" % clock_count)
