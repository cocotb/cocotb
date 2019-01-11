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
    def __init__(self, dut):
        self.dut = dut

        self.clkedge = RisingEdge(dut.clk)

        self.stream_in = AvalonSTDriver(self.dut, "asi", dut.clk)
        self.stream_out = AvalonSTMonitor(self.dut, "aso", dut.clk)
        self.scoreboard = Scoreboard(self.dut, fail_immediately=True)

        self.expected_output = []
        self.scoreboard.add_interface(self.stream_out, self.expected_output)

        self.backpressure = BitDriver(self.dut.aso_ready, self.dut.clk)

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
        exp_data = struct.pack("B",data)
        if sys.version_info >= (3, 0):
            exp_data = exp_data.decode('ascii')
        self.expected_output.append(exp_data)
        yield self.stream_in.send(data)

@cocotb.test(expect_fail=False)
def test_avalon_stream(dut):
    """Test stream of avalon data"""

    tb = AvalonSTTB(dut)
    yield tb.initialise()
    tb.backpressure.start(wave())

    for _ in range(20):
        data = random.randint(0,(2^7)-1)
        yield tb.send_data(data)
        yield tb.clkedge

    for _ in range(5):
        yield tb.clkedge

    raise tb.scoreboard.result
