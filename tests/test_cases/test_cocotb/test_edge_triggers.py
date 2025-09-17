# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for edge triggers

* ValueChange
* RisingEdge
* FallingEdge
* ClockCycles
"""

import os
import re

import pytest
from common import assert_takes

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import (
    ClockCycles,
    Combine,
    FallingEdge,
    First,
    ReadOnly,
    RisingEdge,
    SimTimeoutError,
    Timer,
    ValueChange,
    with_timeout,
)
from cocotb_tools.sim_versions import RivieraVersion

LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()
SIM_NAME = cocotb.SIM_NAME.lower()


async def count_edges_cycles(signal, edges):
    edge = RisingEdge(signal)
    for i in range(edges):
        await edge
        cocotb.log.info("Rising edge %d detected", i)
    cocotb.log.info("Finished, returning %d", edges)
    return edges


async def do_single_edge_check(dut, level):
    """Do test for rising edge"""
    old_value = dut.clk.value
    cocotb.log.info("Value of %s is %d", dut.clk._path, old_value)
    assert old_value != level
    if level == 1:
        await RisingEdge(dut.clk)
    else:
        await FallingEdge(dut.clk)
    assert dut.clk.value == level


@cocotb.test()
async def test_rising_edge(dut):
    """Test that a rising edge can be awaited on"""
    dut.clk.value = 0
    await Timer(1, "ns")
    test = cocotb.start_soon(do_single_edge_check(dut, 1))
    await Timer(10, "ns")
    dut.clk.value = 1
    fail_timer = Timer(1000, "ns")
    result = await First(fail_timer, test)
    assert result is not fail_timer, "Test timed out"


@cocotb.test()
async def test_falling_edge(dut):
    """Test that a falling edge can be awaited on"""
    dut.clk.value = 1
    await Timer(1, "ns")
    test = cocotb.start_soon(do_single_edge_check(dut, 0))
    await Timer(10, "ns")
    dut.clk.value = 0
    fail_timer = Timer(1000, "ns")
    result = await First(fail_timer, test)
    assert result is not fail_timer, "Test timed out"


@cocotb.test()
async def test_either_edge(dut):
    """Test that either edge can be triggered on"""
    dut.clk.value = 0
    await Timer(1, "ns")
    dut.clk.value = 1
    await ValueChange(dut.clk)
    assert dut.clk.value == 1
    await Timer(10, "ns")
    dut.clk.value = 0
    await ValueChange(dut.clk)
    assert dut.clk.value == 0
    await Timer(10, "ns")
    dut.clk.value = 1
    await ValueChange(dut.clk)
    assert dut.clk.value == 1
    await Timer(10, "ns")
    dut.clk.value = 0
    await ValueChange(dut.clk)
    assert dut.clk.value == 0
    await Timer(10, "ns")
    dut.clk.value = 1
    await ValueChange(dut.clk)
    assert dut.clk.value == 1
    await Timer(10, "ns")
    dut.clk.value = 0
    await ValueChange(dut.clk)
    assert dut.clk.value == 0


@cocotb.test()
async def test_fork_and_monitor(dut, period=1000, clocks=6):
    cocotb.start_soon(Clock(dut.clk, period, "ns").start())

    # Ensure the clock has started
    await RisingEdge(dut.clk)

    timer = Timer(period + 10, "ns")
    task = cocotb.start_soon(count_edges_cycles(dut.clk, clocks))
    count = 0
    expect = clocks - 1

    while True:
        result = await First(timer, task)
        assert count <= expect, "Task didn't complete in expected time"
        if result is timer:
            cocotb.log.info("Count %d: Task still running", count)
            count += 1
        else:
            break
    assert count == expect
    assert result == clocks


async def do_clock(dut, limit, period):
    """Simple clock with a limit"""
    wait_period = period / 2
    while limit:
        await Timer(wait_period, "ns")
        dut.clk.value = 0
        await Timer(wait_period, "ns")
        dut.clk.value = 1
        limit -= 1


async def do_edge_count(dut, signal):
    """Count the edges"""
    global edges_seen
    while True:
        await RisingEdge(signal)
        edges_seen += 1


@cocotb.test()
async def test_edge_count(dut):
    """Count the number of edges is as expected"""
    global edges_seen
    edges_seen = 0
    clk_period = 100
    edge_count = 10
    cocotb.start_soon(do_clock(dut, edge_count, clk_period))
    cocotb.start_soon(do_edge_count(dut, dut.clk))

    await Timer(clk_period * (edge_count + 1), "ns")
    assert edge_count == edges_seen


@cocotb.test()
async def test_edge_identity(dut):
    """
    Test that ValueChange triggers returns the same object each time
    """

    re = RisingEdge(dut.clk)
    fe = FallingEdge(dut.clk)
    e = ValueChange(dut.clk)

    assert re is RisingEdge(dut.clk)
    assert fe is FallingEdge(dut.clk)
    assert e is ValueChange(dut.clk)

    # check they are all unique
    assert len({re, fe, e}) == 3
    await Timer(1, "ns")


@cocotb.test
async def test_trigger_result_type(dut) -> None:
    """
    Test that the result of trigger expression have a predictable type
    """
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    r = RisingEdge(dut.clk)
    assert r is dut.clk.rising_edge
    assert (await r) is r
    assert (await dut.clk.rising_edge) is dut.clk.rising_edge

    f = FallingEdge(dut.clk)
    assert f is dut.clk.falling_edge
    assert (await f) is f
    assert (await dut.clk.falling_edge) is dut.clk.falling_edge

    vc = ValueChange(dut.clk)
    assert vc is dut.clk.value_change
    assert (await vc) is vc
    assert (await dut.clk.value_change) is dut.clk.value_change


@cocotb.test()
async def test_clock_cycles(dut):
    """
    Test the ClockCycles Trigger
    """
    clk = dut.clk
    period = 100
    cycles = 10
    cocotb.start_soon(Clock(clk, period, "ns").start())

    # necessary to put us in a consistent state for the cycle count math below
    await RisingEdge(clk)

    t = ClockCycles(clk, cycles, RisingEdge)
    # NVC gives upper-case identifiers for some things, so do case-insensitive match. See gh-3985
    assert re.match(
        r"ClockCycles\(sample_module.clk, 10, RisingEdge\)",
        repr(t),
        flags=re.IGNORECASE,
    )
    assert t.signal is clk
    assert t.num_cycles == cycles
    assert t.edge_type is RisingEdge

    with assert_takes((cycles * period), "ns"):
        await t

    t = ClockCycles(clk, 10, FallingEdge)
    # NVC gives upper-case identifiers for some things, so do case-insensitive match. See gh-3985
    assert re.match(
        r"ClockCycles\(sample_module.clk, 10, FallingEdge\)",
        repr(t),
        flags=re.IGNORECASE,
    )
    assert t.signal is clk
    assert t.num_cycles == cycles
    assert t.edge_type is FallingEdge

    with assert_takes((cycles * period) - (period // 2), "ns"):
        await t

    # test other edge type construction
    assert ClockCycles(clk, cycles, True).edge_type is RisingEdge
    assert ClockCycles(clk, cycles, False).edge_type is FallingEdge
    assert ClockCycles(clk, cycles, edge_type=ValueChange).edge_type is ValueChange
    assert ClockCycles(clk, cycles, rising=True).edge_type is RisingEdge
    assert ClockCycles(clk, cycles, rising=False).edge_type is FallingEdge
    assert ClockCycles(clk, cycles).edge_type is RisingEdge  # default

    # bad construction calls
    with pytest.raises(TypeError):
        ClockCycles(clk, cycles, True, edge_type=RisingEdge)
    with pytest.raises(TypeError):
        ClockCycles(clk, cycles, True, rising=True)
    with pytest.raises(TypeError):
        ClockCycles(clk, cycles, rising=True, edge_type=RisingEdge)
    with pytest.raises(TypeError):
        ClockCycles(clk, cycles, ValueChange, rising=True, edge_type=RisingEdge)


@cocotb.test()
async def test_clock_cycles_forked(dut):
    """Test that ClockCycles can be used in forked coroutines"""
    # gh-520

    cocotb.start_soon(Clock(dut.clk, 100, "ns").start())

    async def wait_ten():
        await ClockCycles(dut.clk, 10)

    a = cocotb.start_soon(wait_ten())
    b = cocotb.start_soon(wait_ten())
    await a
    await b


@cocotb.test(
    timeout_time=100,
    timeout_unit="ns",
    expect_error=(  # gh-2344
        SimTimeoutError
        if (
            LANGUAGE in ["verilog"]
            and SIM_NAME.startswith(("riviera", "aldec"))
            and RivieraVersion(cocotb.SIM_VERSION) < RivieraVersion("2023.04")
        )
        else ()
    ),
)
async def test_both_edge_triggers(dut):
    async def wait_rising_edge():
        await RisingEdge(dut.clk)

    async def wait_falling_edge():
        await FallingEdge(dut.clk)

    rising_coro = cocotb.start_soon(wait_rising_edge())
    falling_coro = cocotb.start_soon(wait_falling_edge())
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await Combine(rising_coro, falling_coro)


@cocotb.test()
async def test_edge_on_vector(dut):
    """Test that ValueChange() triggers on any 0/1 change in a vector"""

    cocotb.start_soon(Clock(dut.clk, 100, "ns").start())

    edge_cnt = 0

    async def wait_edge():
        nonlocal edge_cnt
        while True:
            await ValueChange(dut.stream_out_data_registered)
            if SIM_NAME.startswith("modelsim"):
                await ReadOnly()  # not needed for other simulators
            edge_cnt = edge_cnt + 1

    dut.stream_in_data.value = 0
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    cocotb.start_soon(wait_edge())

    for val in range(1, 2 ** len(dut.stream_in_data) - 1):
        # produce an edge by setting a value != 0:
        dut.stream_in_data.value = val
        await RisingEdge(dut.clk)
        # set back to all-0:
        dut.stream_in_data.value = 0
        await RisingEdge(dut.clk)

    # We have to wait because we don't know the scheduling order of the above
    # ValueChange(dut.stream_out_data_registered) and the above RisingEdge(dut.clk)
    # ValueChange(dut.stream_out_data_registered) should occur strictly after RisingEdge(dut.clk),
    # but NVC and Verilator behave differently.
    await RisingEdge(dut.clk)

    expected_count = 2 * ((2 ** len(dut.stream_in_data) - 1) - 1)

    assert edge_cnt == expected_count


@cocotb.test()
async def test_edge_bad_handles(dut):
    with pytest.raises(TypeError):
        RisingEdge(dut)

    with pytest.raises(TypeError):
        FallingEdge(dut)

    with pytest.raises(TypeError):
        ValueChange(dut)

    with pytest.raises(TypeError):
        RisingEdge(dut.stream_in_data)

    with pytest.raises(TypeError):
        FallingEdge(dut.stream_in_data)


@cocotb.test()
async def test_edge_logic_vector(dut):
    dut.stream_in_data.value = 0

    async def change_stream_in_data():
        await Timer(10, "ns")
        dut.stream_in_data.value = 10

    cocotb.start_soon(change_stream_in_data())

    await with_timeout(ValueChange(dut.stream_in_data), 20, "ns")


# icarus doesn't support integer inputs/outputs
@cocotb.test(skip=SIM_NAME.startswith("icarus"))
async def test_edge_non_logic_handles(dut):
    dut.stream_in_int.value = 0

    async def change_stream_in_int():
        await Timer(10, "ns")
        dut.stream_in_int.value = 10

    cocotb.start_soon(change_stream_in_int())

    await with_timeout(ValueChange(dut.stream_in_int), 20, "ns")


@cocotb.test
async def test_edge_trigger_repr(dut) -> None:
    e = ValueChange(dut.clk)
    # NVC gives upper-case identifiers for some things, so do case-insensitive match. See gh-3985
    assert re.match(
        r"ValueChange\(LogicObject\(sample_module\.clk\)\)",
        repr(e),
        flags=re.IGNORECASE,
    )
    f = RisingEdge(dut.stream_in_ready)
    assert re.match(
        r"RisingEdge\(LogicObject\(sample_module\.stream_in_ready\)\)",
        repr(f),
        flags=re.IGNORECASE,
    )
    g = FallingEdge(dut.stream_in_valid)
    assert re.match(
        r"FallingEdge\(LogicObject\(sample_module\.stream_in_valid\)\)",
        repr(g),
        flags=re.IGNORECASE,
    )


async def test_edge_trigger_on_const(dut) -> None:
    """Test failure if getting Edge trigger on const signal."""
    with pytest.raises(TypeError):
        RisingEdge(dut.INT_PARAM)
    with pytest.raises(TypeError):
        FallingEdge(dut.INT_PARAM)
    with pytest.raises(TypeError):
        ValueChange(dut.INT_PARAM)
    with pytest.raises(TypeError):
        dut.INT_PARAM.value_change


async def wait_for_edge(signal):
    for _ in range(10):
        await ValueChange(signal)


async def wait_for_rising_edge(signal):
    for _ in range(10):
        await RisingEdge(signal)


async def wait_for_falling_edge(signal):
    for _ in range(10):
        await FallingEdge(signal)


@cocotb.test
async def issue_376_all_edges(dut):
    Clock(dut.clk, 2500).start()
    cocotb.start_soon(wait_for_edge(dut.clk))
    cocotb.start_soon(wait_for_rising_edge(dut.clk))
    await cocotb.start_soon(wait_for_falling_edge(dut.clk))


@cocotb.test()
async def issue_376_same_edges(dut):
    Clock(dut.clk, 2500).start()
    cocotb.start_soon(wait_for_rising_edge(dut.clk))
    await cocotb.start_soon(wait_for_rising_edge(dut.clk))


@cocotb.test()
async def issue_376_different_edges(dut):
    Clock(dut.clk, 2500).start()
    cocotb.start_soon(wait_for_rising_edge(dut.clk))
    await cocotb.start_soon(wait_for_falling_edge(dut.clk))
