#!/usr/bin/env python
"""Test to demonstrate functionality of the avalon basic streaming interface"""

import logging
import random
import struct
import sys

import cocotb
from cocotb.drivers import BitDriver
from cocotb.drivers.avalon import AvalonST as AvalonSTDriver
from cocotb.monitors.avalon import AvalonST as AvalonSTMonitor
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
from cocotb.scoreboard import Scoreboard
from cocotb.generators.bit import wave


class AvalonSTTB(object):
    """Testbench for avalon basic stream"""
    def __init__(self, dut, **kwargs):
        self.dut = dut
        self.name_map = kwargs.pop('avalon_stream_name_map', None)

        self.clkedge = RisingEdge(dut.clk)

        self.stream_in = AvalonSTDriver(self.dut, "asi", dut.clk,
                                        name_map=self.name_map)
        self.stream_out = AvalonSTMonitor(self.dut, "aso", dut.clk,
                                          name_map=self.name_map)
        self.scoreboard = Scoreboard(self.dut, fail_immediately=True)

        self.expected_output = []
        self.scoreboard.add_interface(self.stream_out, self.expected_output)

        ready_suffix = "ready"
        if ready_suffix in self.name_map:
            ready_suffix = self.name_map[ready_suffix]
        self.backpressure = BitDriver(getattr(self.dut, "aso_" + ready_suffix),
                                      self.dut.clk)

    @cocotb.coroutine
    def initialise(self):
        self.dut.reset <= 0
        cocotb.fork(Clock(self.dut.clk, 10).start())
        for _ in range(3):
            yield self.clkedge
        self.dut.reset <= 1
        yield self.clkedge

    @cocotb.coroutine
    def send_data(self, data):
        exp_data = struct.pack("B", data)
        if sys.version_info >= (3, 0):
            exp_data = exp_data.decode('ascii')
        self.expected_output.append(exp_data)
        yield self.stream_in.send(data)


@cocotb.test(expect_fail=False)
def test_avalon_stream(dut):
    """Test stream of avalon data"""

    avalon_stream_name_map = {
      'ready': 'RDY',
      'valid': 'VAL',
      'data': 'DAT'
    }
    tb = AvalonSTTB(dut, avalon_stream_name_map=avalon_stream_name_map)
    yield tb.initialise()
    tb.backpressure.start(wave())

    for _ in range(20):
        data = random.randint(0, (2 ^ 7)-1)
        yield tb.send_data(data)
        yield tb.clkedge

    for _ in range(5):
        yield tb.clkedge

    raise tb.scoreboard.result
