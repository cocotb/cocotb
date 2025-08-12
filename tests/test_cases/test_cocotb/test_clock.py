# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests relating to cocotb.clock.Clock
"""

import decimal
import fractions
import os
from typing import Any

import pytest
from common import assert_takes

import cocotb
from cocotb._base_triggers import NullTrigger
from cocotb.clock import Clock
from cocotb.handle import Immediate
from cocotb.simulator import clock_create, get_precision
from cocotb.triggers import (
    FallingEdge,
    RisingEdge,
    SimTimeoutError,
    Timer,
    with_timeout,
)

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test()
@cocotb.parametrize(impl=["gpi", "py"])
async def test_clock_with_units(dut, impl: str) -> None:
    clk_1mhz = Clock(dut.clk, 1.0, unit="us", impl=impl)
    clk_250mhz = Clock(dut.clk, 4, unit="ns", impl=impl)

    assert clk_1mhz.signal is dut.clk
    assert clk_1mhz.period == 1.0
    assert clk_1mhz.unit == "us"
    assert clk_1mhz.impl == impl

    assert str(clk_1mhz) == f"<Clock, {dut.clk._path} @ 1.0 MHz>"
    assert str(clk_250mhz) == f"<Clock, {dut.clk._path} @ 250.0 MHz>"

    clk_1mhz.start()

    with assert_takes(1000, "ns"):
        await Timer(1, "ns")
        await RisingEdge(dut.clk)

    with assert_takes(1000, "ns"):
        await RisingEdge(dut.clk)

    clk_1mhz.stop()

    clk_250mhz.start()

    with assert_takes(4, "ns"):
        await Timer(1, "ns")
        await RisingEdge(dut.clk)

    with assert_takes(4, "ns"):
        await RisingEdge(dut.clk)

    clk_250mhz.stop()


@cocotb.test
async def test_gpi_clock_error_signal_type(_) -> None:
    with pytest.raises(TypeError):
        clock_create(None)


@cocotb.test
async def test_gpi_clock_error_impl(dut):
    with pytest.raises(ValueError):
        Clock(dut.clk, 1.0, unit="step", impl="invalid")


@cocotb.test
async def test_gpi_clock_error_params(dut):
    clk = clock_create(dut.clk._handle)
    with pytest.raises(TypeError):
        clk.start(2, 1)


@cocotb.test
async def test_gpi_clock_error_timing(dut):
    clk = clock_create(dut.clk._handle)
    with pytest.raises(ValueError):
        clk.start(2, 3, True, 0)


@cocotb.test
async def test_bad_period(dut):
    with pytest.raises(ValueError, match="Bad `period`"):
        Clock(dut.clk, 1, unit="step", impl="gpi")
    with pytest.raises(ValueError, match="Bad `period`"):
        Clock(dut.clk, 1, unit="step", impl="py")


@cocotb.test
async def test_gpi_clock_error_already_started(dut):
    clk = clock_create(dut.clk._handle)
    clk.start(2, 1, True, 0)
    with pytest.raises(RuntimeError):
        clk.start(2, 1, True, 0)
    clk.stop()


# Xcelium/VHDL does not correctly report the simulator precision.
# See also https://github.com/cocotb/cocotb/issues/3419
@cocotb.test(skip=(LANGUAGE == "vhdl" and cocotb.SIM_NAME.startswith("xmsim")))
async def test_clocks_with_other_number_types(dut):
    # The following test assumes a time precision of at least 0.1ns.
    # Update the simulator invocation if this assert hits!
    assert get_precision() <= -10

    clk1 = cocotb.start_soon(Clock(dut.clk, decimal.Decimal("1"), unit="ns").start())
    await Timer(10, "ns")
    clk1.cancel()
    clk2 = cocotb.start_soon(Clock(dut.clk, fractions.Fraction(1), unit="ns").start())
    await Timer(10, "ns")
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
async def test_clock_cycles(dut) -> None:
    period_ns = 10
    cycles = 10
    c = Clock(dut.clk, 10, "ns")
    c.start()

    # so we start at a consistent state for math below
    await RisingEdge(dut.clk)

    with assert_takes(cycles * period_ns, "ns"):
        await c.cycles(cycles)

    with assert_takes((cycles * period_ns) - (period_ns // 2), "ns"):
        await c.cycles(cycles, FallingEdge)


@cocotb.test
async def test_clock_task_cancel(dut) -> None:
    c = Clock(dut.clk, 10, "ns")
    task = c.start()

    await RisingEdge(dut.clk)
    task.cancel()

    # Ensure clock is dead.
    with pytest.raises(SimTimeoutError):
        await with_timeout(RisingEdge(dut.clk), 20, "ns")


@cocotb.test
async def test_bad_set_action(dut: Any) -> None:
    with pytest.raises(TypeError):
        Clock(dut.clk, 10, "ns", set_action=1)


# Immediate isn't truly immediate on every simulator,
# and checking just one is sufficient to know it works.
@cocotb.test(skip=not cocotb.SIM_NAME.lower().startswith("verilator"))
async def test_set_action(dut: Any) -> None:
    c = Clock(dut.clk, 10, "ns", set_action=Immediate)

    c.start(start_high=True)
    await NullTrigger()
    assert dut.clk.value == 1

    await Timer(5, "ns")
    await NullTrigger()
    assert dut.clk.value == 0

    assert c.set_action is Immediate


@cocotb.test
async def test_period_high(dut: Any) -> None:
    # Check bad constructions
    with pytest.raises(ValueError, match="Bad `period_high`"):
        Clock(dut.clk, 2, unit="step", period_high=0.5, impl="gpi")
    with pytest.raises(ValueError, match="Bad `period_high`"):
        Clock(dut.clk, 2, unit="step", period_high=0.5, impl="py")
    with pytest.raises(
        ValueError, match="`period_high` must be strictly less than `period`"
    ):
        Clock(dut.clk, 2, unit="step", period_high=10)

    # Check functionality
    c = Clock(dut.clk, 9, "ns", period_high=7)
    c.start()
    await RisingEdge(dut.clk)
    for _ in range(10):
        with assert_takes(7, "ns"):
            await FallingEdge(dut.clk)
        with assert_takes(2, "ns"):
            await RisingEdge(dut.clk)
