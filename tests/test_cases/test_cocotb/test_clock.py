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

import pytest

import cocotb
from cocotb.clock import Clock
from cocotb.simulator import clock_create, get_precision
from cocotb.triggers import FallingEdge, NullTrigger, RisingEdge, Timer
from cocotb.utils import get_sim_time

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test()
@cocotb.parametrize(impl=["gpi", "py"])
async def test_clock_with_units(dut, impl: str) -> None:
    clk_1mhz = Clock(dut.clk, 1.0, units="us", impl=impl)
    clk_250mhz = Clock(dut.clk, 4, units="ns", impl=impl)

    assert clk_1mhz.signal is dut.clk
    assert clk_1mhz.period == 1.0
    assert clk_1mhz.units == "us"
    assert clk_1mhz.impl == impl

    assert str(clk_1mhz) == f"<Clock, {dut.clk._path} @ 1.0 MHz>"
    assert str(clk_250mhz) == f"<Clock, {dut.clk._path} @ 250.0 MHz>"

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


@cocotb.test
async def test_gpi_clock_error_signal_type(_) -> None:
    with pytest.raises(TypeError):
        clock_create(None)


@cocotb.test
async def test_gpi_clock_error_impl(dut):
    with pytest.raises(ValueError):
        Clock(dut.clk, 1.0, units="step", impl="invalid")


@cocotb.test
async def test_gpi_clock_error_params(dut):
    clk = clock_create(dut.clk._handle)
    with pytest.raises(TypeError):
        clk.start(2, 1)


@cocotb.test
async def test_gpi_clock_error_timing(dut):
    clk = clock_create(dut.clk._handle)
    with pytest.raises(ValueError):
        clk.start(2, 3, True)


@cocotb.test
async def test_gpi_clock_error_start(dut):
    clk = Clock(dut.clk, 1.0, units="step", impl="gpi")
    with pytest.raises(ValueError):
        clk.start()


@cocotb.test
async def test_gpi_clock_error_already_started(dut):
    clk = clock_create(dut.clk._handle)
    clk.start(2, 1, True)
    with pytest.raises(RuntimeError):
        clk.start(2, 1, True)
    clk.stop()


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


@cocotb.test
async def test_clock_stop_and_restart(dut) -> None:
    c = Clock(dut.clk, 10, "ns")
    c.start()
    for _ in range(10):
        await RisingEdge(dut.clk)
    with pytest.raises(RuntimeError):
        c.start()
    c.stop()
    with pytest.raises(RuntimeError):
        c.stop()
    c.start()
    for _ in range(10):
        await RisingEdge(dut.clk)


@cocotb.test
async def test_clock_stop_and_restart_by_killing(dut) -> None:
    c = Clock(dut.clk, 10, "ns")
    task = c.start()
    for _ in range(10):
        await RisingEdge(dut.clk)
    with pytest.warns(FutureWarning):
        task.cancel()
    await NullTrigger()  # cancel() schedules the done callback
    c.start()
    for _ in range(10):
        await RisingEdge(dut.clk)


@cocotb.test
async def test_clock_cycles(dut) -> None:
    period_ns = 10
    cycles = 10
    c = Clock(dut.clk, 10, "ns")
    c.start()

    # so we start at a consistent state for math below
    await RisingEdge(dut.clk)

    start_time = get_sim_time(units="ns")
    await c.cycles(cycles)
    end_time = get_sim_time(units="ns")
    assert end_time == (start_time + (cycles * period_ns))

    start_time = get_sim_time(units="ns")
    await c.cycles(cycles, FallingEdge)
    end_time = get_sim_time(units="ns")
    assert end_time == (start_time + (cycles * period_ns) - (period_ns // 2))
