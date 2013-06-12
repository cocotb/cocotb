#!/bin/python

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
    Test bench for issue 12


    Expected behaviour over 6 clock cycles

    start of day
        ready <= 0


    clock tick 1
        drive ready to 1
        drive 1 onto data in
        data_out_comb changes to 1

    clock tick 2
        drive ready to 0
        data_out_registered changes to 1 (driven by process inside the sim)

    etc.

"""

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, Edge, Event, RisingEdge, ReadOnly
from cocotb.clock import Clock

@coroutine
def ready_fiddler(clock, ready):
    """Assert ready every other clock cycle"""
    v = 0
    ready <= v
    while True:
        yield RisingEdge(clock)
        v = not v
        ready <= v

@coroutine
def driver(clock, ready, data):
    """Drives incrementing values onto a bus each time ready is high"""
    data <= 0
    while True:
        yield RisingEdge(ready)
        data <= data.value.value + 1

@coroutine
def issue12(dut):
    dut.log.info("Test got DUT:" + str(dut))
    
    # convenience
    clock = dut.clk
    ready = dut.stream_in_ready
    dout_comb = dut.stream_out_data_comb
    dout_regd = dut.stream_out_data_registered

    clock <= 0

    dut.stream_out_ready <= 0

    real_clock = Clock(clock, 1000)
    yield Timer(1000)

    # kick off the coroutines
    rdys = cocotb.scheduler.add(ready_fiddler(dut.clk, dut.stream_out_ready))
    drvr = cocotb.scheduler.add(driver(dut.clk, dut.stream_in_ready, dut.stream_in_data))

    yield Timer(1000)
    real_clock.start(12)

    expected_comb = 0
    expected_regd = 0
    failed = 0

    for clock_tick in range(6):
        yield RisingEdge(dut.clk)
        yield ReadOnly()
        if ready.value.value: expected_comb += 1
        dut.log.info("ready: %s\tdout_comb: %d\tdout_regd: %d" % (ready.value.value, dout_comb.value.value, dout_regd.value.value))
        if dout_comb.value.value != expected_comb:
            dut.log.error("Expected dout_comb to be %d but got %d" % (expected_comb, dout_comb.value.value))
            failed += 1
        if dout_regd.value.value != expected_regd:
            dut.log.error("Expected dout_regd to be %d but got %d" % (expected_regd, dout_regd.value.value))
            failed += 1
        expected_regd = expected_comb

    # FIXME the sim exits when the cgen finishes but we still want this code to run
    # If caching writes then this code is run, if not then we exit prematurely
    dut.log.info("test complete!")
    if failed:
        dut.log.critical("%d failures!" % (failed))
    else:
        dut.log.warn("Test Passed")

