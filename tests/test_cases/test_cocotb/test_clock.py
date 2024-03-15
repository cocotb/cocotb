# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.clock.Clock
"""

import decimal
import fractions
import os
from math import isclose

import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.simulator import get_precision
from cocotb.triggers import RisingEdge, Timer
from cocotb.utils import get_sim_time

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test()
async def test_clock_with_units(dut):
    clk_1mhz = Clock(dut.clk, 1.0, units="us")
    clk_250mhz = Clock(dut.clk, 4.0, units="ns")

    assert str(clk_1mhz) == "Clock(1.0 MHz)"
    dut._log.info(f"Created clock >{str(clk_1mhz)}<")

    assert str(clk_250mhz) == "Clock(250.0 MHz)"
    dut._log.info(f"Created clock >{str(clk_250mhz)}<")

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


# Xcelium/VHDL does not correctly report the simulator precision.
# See also https://github.com/cocotb/cocotb/issues/3419
@cocotb.test(skip=(LANGUAGE == "vhdl" and cocotb.SIM_NAME.startswith("xmsim")))
async def test_clocks_with_other_number_types(dut):
    # The following test assumes a time precision of at least 0.1ns.
    # Update the simulator invocation if this assert hits!
    assert get_precision() <= -10

    clk1 = cocotb.start_soon(Clock(dut.clk, decimal.Decimal("1"), units="ns").start())
    await Timer(10, "ns")
    with pytest.warns(FutureWarning, match="cause a CancelledError to be thrown"):
        clk1.cancel()
    clk2 = cocotb.start_soon(Clock(dut.clk, fractions.Fraction(1), units="ns").start())
    await Timer(10, "ns")
    with pytest.warns(FutureWarning, match="cause a CancelledError to be thrown"):
        clk2.cancel()
