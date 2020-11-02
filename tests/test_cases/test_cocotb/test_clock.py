# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.clock.Clock
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge
from cocotb.result import TestFailure
from cocotb.utils import get_sim_time
from math import isclose


@cocotb.test(expect_fail=False)
def test_clock_with_units(dut):
    clk_1mhz   = Clock(dut.clk, 1.0, units='us')
    clk_250mhz = Clock(dut.clk, 4.0, units='ns')

    if str(clk_1mhz) != "Clock(1.0 MHz)":
        raise TestFailure("{} != 'Clock(1.0 MHz)'".format(str(clk_1mhz)))
    else:
        dut._log.info('Created clock >{}<'.format(str(clk_1mhz)))

    if str(clk_250mhz) != "Clock(250.0 MHz)":
        raise TestFailure("{} != 'Clock(250.0 MHz)'".format(str(clk_250mhz)))
    else:
        dut._log.info('Created clock >{}<'.format(str(clk_250mhz)))

    clk_gen = cocotb.fork(clk_1mhz.start())

    start_time_ns = get_sim_time(units='ns')

    yield Timer(1)

    yield RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 1000.0):
        raise TestFailure("Expected a period of 1 us")

    start_time_ns = edge_time_ns

    yield RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 1000.0):
        raise TestFailure("Expected a period of 1 us")

    clk_gen.kill()

    clk_gen = cocotb.fork(clk_250mhz.start())

    start_time_ns = get_sim_time(units='ns')

    yield Timer(1)

    yield RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 4.0):
        raise TestFailure("Expected a period of 4 ns")

    start_time_ns = edge_time_ns

    yield RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units='ns')
    if not isclose(edge_time_ns, start_time_ns + 4.0):
        raise TestFailure("Expected a period of 4 ns")

    clk_gen.kill()


@cocotb.test(expect_fail=False)
def test_external_clock(dut):
    """Test ability to yield on an external non-cocotb coroutine decorated function"""
    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())
    count = 0
    while count != 100:
        yield RisingEdge(dut.clk)
        count += 1
    clk_gen.kill()
