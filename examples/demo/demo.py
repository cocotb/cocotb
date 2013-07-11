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
    Example usage of the testbench framework
"""

from cocotb.handle import *
import cocotb, simulator
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, Edge, Event

@coroutine
def clock_generator(signal):
    for i in range(10):
        signal <= 0
        yield Timer(1000)
        signal <= 1
        yield Timer(1000)
    signal.log.warning("Clock generator finished!")

@coroutine
def clock_monitor(signal, output):
    while True:
        yield Edge(signal)
        signal.log.info("Edge triggered:  %s : %s = %s" % (signal.getvalue().value, str(output), output.getvalue().value))


@coroutine
def reset_dut(clock, reset, enable):
    clock_ticks = 0
    reset <= 1
    enable <= 0
    while True:
        yield Edge(clock)
        clock_ticks += 1
        if clock_ticks >= 4:
            reset <= 0
            enable <= 1
            break
    reset.log.info("Released reset: %s" % reset.getvalue())


@coroutine
def waiting_coroutine(some_event):
    some_event.log.info("Putting waiting coroutine to sleep until this event fires")
    yield some_event.wait()
    some_event.log.info("Coroutine woke up again!  Awesome")

@cocotb.test()
def example_test(dut):
    """This is an example test"""
    dut.log.info("Example test got DUT:" + str(dut))

    yield Timer(10000)

    clk = dut.clock
    enable = dut.enable
    reset = dut.reset
    count = dut.counter_out

    dut.log.info(str(clk))

    cgen = cocotb.scheduler.add(clock_generator(clk))
    yield reset_dut(clk, reset, enable)
    dut.log.info("Reset DUT complete, continuing test...")
    cmon = cocotb.scheduler.add(clock_monitor(clk, count))

    dut.log.info("Blocking test until the clock generator finishes...")
    yield cgen.join()

    sync = Event()
    cocotb.scheduler.add(waiting_coroutine(sync))
    yield Timer(10000)
    dut.log.info("Waking up the waiting coroutine with an event...")
    sync.set()
    yield Timer(10000)


    result = yield Timer(1000000)
    dut.log.warning("test complete!")


@cocotb.test()
def example_test2(dut):
    """This is another example test"""
    result = yield Timer(1000000) 
    dut.log.warning("test complete!")
