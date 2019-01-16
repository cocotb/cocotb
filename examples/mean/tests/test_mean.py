from __future__ import print_function
from __future__ import division

import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.result import TestFailure
from cocotb.monitors import BusMonitor
from cocotb.scoreboard import Scoreboard

import random

clock_period = 100


class StreamBusMonitor(BusMonitor):
    """Streaming bus monitor."""
    
    _signals = ["valid", "data"]

    @cocotb.coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transactions."""

        while True:
            yield RisingEdge(self.clock)
            yield ReadOnly()
            if self.bus.valid.value:
                self._recv(int(self.bus.data.value))


@cocotb.coroutine
def clock_gen(signal, period=10000):
    while True:
        signal <= 0
        yield Timer(period/2)
        signal <= 1
        yield Timer(period/2)


@cocotb.coroutine
def value_test(dut, num):
    """Test n*num/n = num"""

    data_width = int(dut.DATA_WIDTH.value)
    bus_width = int(dut.BUS_WIDTH.value)
    dut._log.info('Detected DATA_WIDTH = %d, BUS_WIDTH = %d' %
                 (data_width, bus_width))

    cocotb.fork(clock_gen(dut.clk, period=clock_period))

    dut.rst <= 1
    for i in range(bus_width):
        dut.i_data[i] <= 0
    dut.i_valid <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0

    for i in range(bus_width):
        dut.i_data[i] <= num
    dut.i_valid <= 1
    yield RisingEdge(dut.clk)
    dut.i_valid <= 0
    yield RisingEdge(dut.clk)
    got = int(dut.o_data.value)

    if got != num:
        raise TestFailure(
            'Mismatch detected: got %d, exp %d!' % (got, num))


@cocotb.test()
def mean_basic_test(dut):
    """Test n*5/n = 5"""
    yield value_test(dut, 5)


@cocotb.test()
def mean_overflow_test(dut):
    """Test for overflow n*max_val/n = max_val"""
    data_width = int(dut.DATA_WIDTH.value)
    yield value_test(dut, 2**data_width - 1)


@cocotb.test()
def mean_randomised_test(dut):
    """Test mean of random numbers multiple times"""

    # dut_in = StreamBusMonitor(dut, "i", dut.clk)  # this doesn't work:
    # VPI Error vpi_get_value():
    # ERROR - Cannot get a value for an object of type vpiArrayVar.

    dut_out = StreamBusMonitor(dut, "o", dut.clk)

    exp_out = []
    scoreboard = Scoreboard(dut)
    scoreboard.add_interface(dut_out, exp_out)

    data_width = int(dut.DATA_WIDTH.value)
    bus_width = int(dut.BUS_WIDTH.value)
    dut._log.info('Detected DATA_WIDTH = %d, BUS_WIDTH = %d' %
                 (data_width, bus_width))

    cocotb.fork(clock_gen(dut.clk, period=clock_period))

    dut.rst <= 1
    for i in range(bus_width):
        dut.i_data[i] = 0
    dut.i_valid <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0

    for j in range(10):
        nums = []
        for i in range(bus_width):
            x = random.randint(0, 2**data_width - 1)
            dut.i_data[i] = x
            nums.append(x)
        dut.i_valid <= 1

        nums_mean = sum(nums) // bus_width
        exp_out.append(nums_mean)
        yield RisingEdge(dut.clk)
        dut.i_valid <= 0
