# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.clock.Clock
"""
from math import isclose

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.utils import get_sim_time


@cocotb.test()
async def test_clock_with_units(dut):
    clk_1mhz = Clock(dut.clk, 1.0, units="us")
    clk_250mhz = Clock(dut.clk, 4.0, units="ns")

    assert str(clk_1mhz) == "Clock(1.0 MHz)"
    dut._log.info("Created clock >{}<".format(str(clk_1mhz)))

    assert str(clk_250mhz) == "Clock(250.0 MHz)"
    dut._log.info("Created clock >{}<".format(str(clk_250mhz)))

    clk_gen = cocotb.start_soon(clk_1mhz.start())

    start_time_ns = get_sim_time(units="ns")

    await Timer(1, "ns")
    await RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units="ns")
    assert isclose(edge_time_ns, start_time_ns + 1000.0), "Expected a period of 1 us"

    start_time_ns = edge_time_ns

    await RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units="ns")
    assert isclose(edge_time_ns, start_time_ns + 1000.0), "Expected a period of 1 us"

    clk_gen.kill()

    clk_gen = await cocotb.start(clk_250mhz.start())

    start_time_ns = get_sim_time(units="ns")

    await Timer(1, "ns")
    await RisingEdge(dut.clk)

    edge_time_ns = get_sim_time(units="ns")
    assert isclose(edge_time_ns, start_time_ns + 4.0), "Expected a period of 4 ns"

    start_time_ns = edge_time_ns

    await RisingEdge(dut.clk)
    edge_time_ns = get_sim_time(units="ns")
    assert isclose(edge_time_ns, start_time_ns + 4.0), "Expected a period of 4 ns"

    clk_gen.kill()


@cocotb.test()
async def test_external_clock(dut):
    """Test awaiting on an external non-cocotb coroutine decorated function"""
    clk_gen = cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    count = 0
    while count != 100:
        await RisingEdge(dut.clk)
        count += 1
    clk_gen.kill()
