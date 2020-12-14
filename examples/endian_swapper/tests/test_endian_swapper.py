# Copyright (c) 2013 Potential Ventures Ltd
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

import random
import logging
import warnings

import cocotb

from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.regression import TestFactory

from cocotb_bus.drivers import BitDriver
from cocotb_bus.drivers.avalon import AvalonSTPkts as AvalonSTDriver
from cocotb_bus.drivers.avalon import AvalonMaster
from cocotb_bus.monitors.avalon import AvalonSTPkts as AvalonSTMonitor
from cocotb_bus.scoreboard import Scoreboard

# Data generators
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    from cocotb.generators.byte import random_data, get_bytes
    from cocotb.generators.bit import wave, intermittent_single_cycles, random_50_percent


async def stream_out_config_setter(dut, stream_out, stream_in):
    """Coroutine to monitor the DUT configuration at the start
       of each packet transfer and set the endianness of the
       output stream accordingly"""
    edge = RisingEdge(dut.stream_in_startofpacket)
    ro = ReadOnly()
    while True:
        await edge
        await ro
        if dut.byteswapping.value:
            stream_out.config['firstSymbolInHighOrderBits'] = \
                not stream_in.config['firstSymbolInHighOrderBits']
        else:
            stream_out.config['firstSymbolInHighOrderBits'] = \
                stream_in.config['firstSymbolInHighOrderBits']


class EndianSwapperTB(object):

    def __init__(self, dut, debug=False):
        self.dut = dut
        self.stream_in = AvalonSTDriver(dut, "stream_in", dut.clk)
        self.backpressure = BitDriver(self.dut.stream_out_ready, self.dut.clk)
        self.stream_out = AvalonSTMonitor(dut, "stream_out", dut.clk,
                                          config={'firstSymbolInHighOrderBits':
                                                  True})

        self.csr = AvalonMaster(dut, "csr", dut.clk)

        cocotb.fork(stream_out_config_setter(dut, self.stream_out,
                                             self.stream_in))

        # Create a scoreboard on the stream_out bus
        self.pkts_sent = 0
        self.expected_output = []
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.stream_out, self.expected_output)

        # Reconstruct the input transactions from the pins
        # and send them to our 'model'
        self.stream_in_recovered = AvalonSTMonitor(dut, "stream_in", dut.clk,
                                                   callback=self.model)

        # Set verbosity on our various interfaces
        level = logging.DEBUG if debug else logging.WARNING
        self.stream_in.log.setLevel(level)
        self.stream_in_recovered.log.setLevel(level)

    def model(self, transaction):
        """Model the DUT based on the input transaction"""
        self.expected_output.append(transaction)
        self.pkts_sent += 1

    async def reset(self, duration=20):
        self.dut._log.debug("Resetting DUT")
        self.dut.reset_n <= 0
        self.stream_in.bus.valid <= 0
        await Timer(duration, units='ns')
        await RisingEdge(self.dut.clk)
        self.dut.reset_n <= 1
        self.dut._log.debug("Out of reset")


async def run_test(dut, data_in=None, config_coroutine=None, idle_inserter=None,
                   backpressure_inserter=None):

    cocotb.fork(Clock(dut.clk, 10, units='ns').start())
    tb = EndianSwapperTB(dut)

    await tb.reset()
    dut.stream_out_ready <= 1

    # Start off any optional coroutines
    if config_coroutine is not None:
        cocotb.fork(config_coroutine(tb.csr))
    if idle_inserter is not None:
        tb.stream_in.set_valid_generator(idle_inserter())
    if backpressure_inserter is not None:
        tb.backpressure.start(backpressure_inserter())

    # Send in the packets
    for transaction in data_in():
        await tb.stream_in.send(transaction)

    # Wait at least 2 cycles where output ready is low before ending the test
    for i in range(2):
        await RisingEdge(dut.clk)
        while not dut.stream_out_ready.value:
            await RisingEdge(dut.clk)

    pkt_count = await tb.csr.read(1)

    assert pkt_count.integer == tb.pkts_sent, "DUT recorded %d packets but tb counted %d" % (pkt_count.integer, tb.pkts_sent)
    dut._log.info("DUT correctly counted %d packets" % pkt_count.integer)

    raise tb.scoreboard.result


def random_packet_sizes(min_size=1, max_size=150, npackets=10):
    """random string data of a random length"""
    for i in range(npackets):
        yield get_bytes(random.randint(min_size, max_size), random_data())


async def randomly_switch_config(csr):
    """Twiddle the byteswapping config register"""
    while True:
        await csr.write(0, random.randint(0, 1))


factory = TestFactory(run_test)
factory.add_option("data_in",
                   [random_packet_sizes])
factory.add_option("config_coroutine",
                   [None, randomly_switch_config])
factory.add_option("idle_inserter",
                   [None, wave, intermittent_single_cycles, random_50_percent])
factory.add_option("backpressure_inserter",
                   [None, wave, intermittent_single_cycles, random_50_percent])
factory.generate_tests()

import cocotb.wavedrom


@cocotb.test()
async def wavedrom_test(dut):
    """
    Generate a JSON wavedrom diagram of a trace and save it to wavedrom.json
    """
    cocotb.fork(Clock(dut.clk, 10, units='ns').start())
    await RisingEdge(dut.clk)
    tb = EndianSwapperTB(dut)
    await tb.reset()

    with cocotb.wavedrom.trace(dut.reset_n, tb.csr.bus, clk=dut.clk) as waves:
        await RisingEdge(dut.clk)
        await tb.csr.read(0)
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        dut._log.info(waves.dumpj(header={'text':'WaveDrom example', 'tick':0}))
        waves.write('wavedrom.json', header={'tick':0}, config={'hscale':3})
