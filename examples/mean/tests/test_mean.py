# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly

from cocotb_bus.scoreboard import Scoreboard
from cocotb_bus.monitors import BusMonitor

import random
import warnings

CLK_PERIOD_NS = 100


class StreamBusMonitor(BusMonitor):
    """Streaming bus monitor."""

    _signals = ["valid", "data"]

    async def _monitor_recv(self):
        """Watch the pins and reconstruct transactions."""

        while True:
            await RisingEdge(self.clock)
            await ReadOnly()
            if self.bus.valid.value:
                self._recv(int(self.bus.data.value))


async def value_test(dut, nums):
    """Test sum(nums)/n"""
    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    BUS_WIDTH = int(dut.BUS_WIDTH.value)
    dut._log.info('Detected DATA_WIDTH = %d, BUS_WIDTH = %d' %
                  (DATA_WIDTH, BUS_WIDTH))

    cocotb.fork(Clock(dut.clk, CLK_PERIOD_NS, units='ns').start())

    dut.rst <= 1
    for i in range(BUS_WIDTH):
        dut.i_data[i] <= 0
    dut.i_valid <= 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst <= 0

    for i in range(BUS_WIDTH):
        dut.i_data[i] <= nums[i]
    dut.i_valid <= 1
    await RisingEdge(dut.clk)
    dut.i_valid <= 0
    await RisingEdge(dut.clk)
    got = int(dut.o_data.value)

    exp = sum(nums) // BUS_WIDTH

    assert got == exp, "Mismatch detected: got {}, expected {}!".format(got, exp)


@cocotb.test()
async def mean_basic_test(dut):
    """Test n*5/n = 5"""
    BUS_WIDTH = int(dut.BUS_WIDTH.value)
    await value_test(dut, [5] * BUS_WIDTH)


@cocotb.test()
async def mean_range_test(dut):
    """Test range(n)/n"""
    BUS_WIDTH = int(dut.BUS_WIDTH.value)
    await value_test(dut, range(1, BUS_WIDTH + 1))


@cocotb.test()
async def mean_overflow_test(dut):
    """Test for overflow n*max_val/n = max_val"""
    BUS_WIDTH = int(dut.BUS_WIDTH.value)
    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    await value_test(dut, [2**DATA_WIDTH - 1] * BUS_WIDTH)


@cocotb.test()
async def mean_randomised_test(dut):
    """Test mean of random numbers multiple times"""

    # dut_in = StreamBusMonitor(dut, "i", dut.clk)  # this doesn't work:
    # VPI Error vpi_get_value():
    # ERROR - Cannot get a value for an object of type vpiArrayVar.

    dut_out = StreamBusMonitor(dut, "o", dut.clk)

    exp_out = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        scoreboard = Scoreboard(dut)
    scoreboard.add_interface(dut_out, exp_out)

    DATA_WIDTH = int(dut.DATA_WIDTH.value)
    BUS_WIDTH = int(dut.BUS_WIDTH.value)
    dut._log.info('Detected DATA_WIDTH = %d, BUS_WIDTH = %d' %
                  (DATA_WIDTH, BUS_WIDTH))

    cocotb.fork(Clock(dut.clk, CLK_PERIOD_NS, units='ns').start())

    dut.rst <= 1
    for i in range(BUS_WIDTH):
        dut.i_data[i] <= 0
    dut.i_valid <= 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst <= 0

    for j in range(10):
        nums = []
        for i in range(BUS_WIDTH):
            x = random.randint(0, 2**DATA_WIDTH - 1)
            dut.i_data[i] <= x
            nums.append(x)
        dut.i_valid <= 1

        nums_mean = sum(nums) // BUS_WIDTH
        exp_out.append(nums_mean)
        await RisingEdge(dut.clk)
        dut.i_valid <= 0

    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
