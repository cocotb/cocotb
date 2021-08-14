# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for edge triggers

* Edge
* RisingEdge
* FallingEdge
* ClockCycles
"""
import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Edge, Timer, ClockCycles, First, Combine, ReadOnly
from cocotb.clock import Clock
from cocotb.result import SimTimeoutError


async def count_edges_cycles(signal, edges):
    edge = RisingEdge(signal)
    for i in range(edges):
        await edge
        signal._log.info("Rising edge %d detected" % i)
    signal._log.info("Finished, returning %d" % edges)
    return edges


async def do_single_edge_check(dut, level):
    """Do test for rising edge"""
    old_value = dut.clk.value.integer
    dut._log.info("Value of %s is %d" % (dut.clk._path, old_value))
    assert old_value != level, "%s not to %d start with" % (dut.clk._path, not level)
    if level == 1:
        await RisingEdge(dut.clk)
    else:
        await FallingEdge(dut.clk)
    new_value = dut.clk.value.integer
    dut._log.info("Value of %s is %d" % (dut.clk._path, new_value))
    assert new_value == level, "%s not %d at end" % (dut.clk._path, level)


@cocotb.test()
async def test_rising_edge(dut):
    """Test that a rising edge can be awaited on"""
    dut.clk.value = 0
    await Timer(1, "ns")
    test = cocotb.fork(do_single_edge_check(dut, 1))
    await Timer(10, "ns")
    dut.clk.value = 1
    fail_timer = Timer(1000, "ns")
    result = await First(fail_timer, test.join())
    assert result is not fail_timer, "Test timed out"


@cocotb.test()
async def test_falling_edge(dut):
    """Test that a falling edge can be awaited on"""
    dut.clk.value = 1
    await Timer(1, "ns")
    test = cocotb.fork(do_single_edge_check(dut, 0))
    await Timer(10, "ns")
    dut.clk.value = 0
    fail_timer = Timer(1000, "ns")
    result = await First(fail_timer, test.join())
    assert result is not fail_timer, "Test timed out"


@cocotb.test()
async def test_either_edge(dut):
    """Test that either edge can be triggered on"""
    dut.clk.value = 0
    await Timer(1, "ns")
    dut.clk.value = 1
    await Edge(dut.clk)
    assert dut.clk.value.integer == 1
    await Timer(10, "ns")
    dut.clk.value = 0
    await Edge(dut.clk)
    assert dut.clk.value.integer == 0
    await Timer(10, "ns")
    dut.clk.value = 1
    await Edge(dut.clk)
    assert dut.clk.value.integer == 1
    await Timer(10, "ns")
    dut.clk.value = 0
    await Edge(dut.clk)
    assert dut.clk.value.integer == 0
    await Timer(10, "ns")
    dut.clk.value = 1
    await Edge(dut.clk)
    assert dut.clk.value.integer == 1
    await Timer(10, "ns")
    dut.clk.value = 0
    await Edge(dut.clk)
    assert dut.clk.value.integer == 0


@cocotb.test()
async def test_fork_and_monitor(dut, period=1000, clocks=6):
    cocotb.fork(Clock(dut.clk, period, "ns").start())

    # Ensure the clock has started
    await RisingEdge(dut.clk)

    timer = Timer(period + 10, "ns")
    task = cocotb.fork(count_edges_cycles(dut.clk, clocks))
    count = 0
    expect = clocks - 1

    while True:
        result = await First(timer, task.join())
        assert count <= expect, "Task didn't complete in expected time"
        if result is timer:
            dut._log.info("Count %d: Task still running" % count)
            count += 1
        else:
            break
    assert count == expect, "Expected to monitor the task %d times but got %d" % (expect, count)
    assert result == clocks, "Expected task to return %d but got %s" % (clocks, repr(result))


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
    clock = cocotb.fork(do_clock(dut, edge_count, clk_period))
    test = cocotb.fork(do_edge_count(dut, dut.clk))

    await Timer(clk_period * (edge_count + 1), "ns")
    assert edge_count == edges_seen, "Correct edge count failed - saw %d, wanted %d" % (edges_seen, edge_count)


@cocotb.test()
async def test_edge_identity(dut):
    """
    Test that Edge triggers returns the same object each time
    """

    re = RisingEdge(dut.clk)
    fe = FallingEdge(dut.clk)
    e = Edge(dut.clk)

    assert re is RisingEdge(dut.clk)
    assert fe is FallingEdge(dut.clk)
    assert e is Edge(dut.clk)

    # check they are all unique
    assert len({re, fe, e}) == 3
    await Timer(1, "ns")


@cocotb.test()
async def test_singleton_isinstance(dut):
    """
    Test that the result of trigger expression have a predictable type
    """
    assert isinstance(RisingEdge(dut.clk), RisingEdge)
    assert isinstance(FallingEdge(dut.clk), FallingEdge)
    assert isinstance(Edge(dut.clk), Edge)

    await Timer(1, "ns")


@cocotb.test()
async def test_clock_cycles(dut):
    """
    Test the ClockCycles Trigger
    """
    clk = dut.clk
    clk_gen = cocotb.fork(Clock(clk, 100, "ns").start())
    await RisingEdge(clk)
    dut._log.info("After one edge")
    await ClockCycles(clk, 10)
    dut._log.info("After 10 edges")


@cocotb.test()
async def test_clock_cycles_forked(dut):
    """ Test that ClockCycles can be used in forked coroutines """
    # gh-520

    clk_gen = cocotb.fork(Clock(dut.clk, 100, "ns").start())

    async def wait_ten():
        await ClockCycles(dut.clk, 10)

    a = cocotb.fork(wait_ten())
    b = cocotb.fork(wait_ten())
    await a.join()
    await b.join()


@cocotb.test(
    timeout_time=100,
    timeout_unit="ns",
    expect_error=(
        SimTimeoutError if (
            cocotb.LANGUAGE in ["verilog"] and
            cocotb.SIM_NAME.lower().startswith(("riviera", "aldec"))  # gh-2344
        )
        else ()
    ),
)
async def test_both_edge_triggers(dut):
    async def wait_rising_edge():
        await RisingEdge(dut.clk)

    async def wait_falling_edge():
        await FallingEdge(dut.clk)

    rising_coro = cocotb.fork(wait_rising_edge())
    falling_coro = cocotb.fork(wait_falling_edge())
    cocotb.fork(Clock(dut.clk, 10, units='ns').start())
    await Combine(rising_coro, falling_coro)


@cocotb.test()
async def test_edge_on_vector(dut):
    """Test that Edge() triggers on any 0/1 change in a vector"""

    cocotb.fork(Clock(dut.clk, 100, "ns").start())

    edge_cnt = 0

    async def wait_edge():
        nonlocal edge_cnt
        while True:
            await Edge(dut.stream_out_data_registered)
            if cocotb.SIM_NAME.lower().startswith("modelsim"):
                await ReadOnly()  # not needed for other simulators
            edge_cnt = edge_cnt + 1

    cocotb.fork(wait_edge())

    dut.stream_in_data.value = 0
    await RisingEdge(dut.clk)

    for val in range(1, 2**len(dut.stream_in_data)-1):
        # produce an edge by setting a value != 0:
        dut.stream_in_data.value = val
        await RisingEdge(dut.clk)
        # set back to all-0:
        dut.stream_in_data.value = 0
        await RisingEdge(dut.clk)

    assert edge_cnt == 2 * ((2**len(dut.stream_in_data)-1)-1)
