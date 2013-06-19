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
    Smoketest to bring up drivers and monitors
"""

import cocotb
from cocotb.generators import feeds
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, Edge, Event
from cocotb.drivers.solarflare import SFStreaming as SFDrv
from cocotb.monitors.solarflare import SFStreaming as SFMon
from cocotb.generators.feeds.itch_feed import *

from modules.sf_streaming.model.sf_streaming import SFStreamingPacket

@coroutine
def clock_generator(signal, period_ps):
    t = Timer(period_ps)
    while True:
        signal <= 0
        yield t
        signal <= 1
        yield t

@cocotb.test()
def smoketest(dut):
    """Smoke test to help get cocotb up and running"""
    dut.log.info("Test started, got DUT:" + str(dut))

    clock_gen = cocotb.scheduler.add(clock_generator(dut.clk, 3200))
    dut.log.info("Clock started...")

    dut.stream_in_ready <= 1

    yield Timer(32000)

    stream_in = SFDrv(dut, "stream_in", dut.clk)
    stream_out = SFMon(dut, "stream_out", dut.clk)

    yield Timer(32000)

    test_feed = ItchFeed("test itch", 1234, 13)
    test_feed.addmsg("An Itch format message")
    test_feed.addmsg("Another Itch format message")
    test_feed.addmsg("The last Itch test")

    for repeat in range(2):
        stream_in.append(SFStreamingPacket(test_feed.getmsg()))

    final_pkt = Event("final_packet")
    stream_in.append(SFStreamingPacket(test_feed.getmsg()), event=final_pkt)

    dut.log.info("Waiting for all packets to be sent...")
    yield final_pkt.wait()
    dut.log.info("All packets sent, cleaning up...")
    yield Timer(32000)
    clock_gen.kill()
    dut.log.warning("Test complete!")
