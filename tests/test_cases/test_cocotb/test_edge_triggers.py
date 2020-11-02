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
from cocotb.triggers import RisingEdge, FallingEdge, Edge, Timer, ClockCycles
from cocotb.clock import Clock


@cocotb.coroutine
def count_edges_cycles(signal, edges):
    edge = RisingEdge(signal)
    for i in range(edges):
        yield edge
        signal._log.info("Rising edge %d detected" % i)
    signal._log.info("Finished, returning %d" % edges)
    return edges


@cocotb.coroutine
def do_single_edge_check(dut, level):
    """Do test for rising edge"""
    old_value = dut.clk.value.integer
    dut._log.info("Value of %s is %d" % (dut.clk._path, old_value))
    assert old_value != level, "%s not to %d start with" % (dut.clk._path, not level)
    if level == 1:
        yield RisingEdge(dut.clk)
    else:
        yield FallingEdge(dut.clk)
    new_value = dut.clk.value.integer
    dut._log.info("Value of %s is %d" % (dut.clk._path, new_value))
    assert new_value == level, "%s not %d at end" % (dut.clk._path, level)


@cocotb.test()
def test_rising_edge(dut):
    """Test that a rising edge can be yielded on"""
    dut.clk <= 0
    yield Timer(1)
    test = cocotb.fork(do_single_edge_check(dut, 1))
    yield Timer(10)
    dut.clk <= 1
    fail_timer = Timer(1000)
    result = yield [fail_timer, test.join()]
    assert result is not fail_timer, "Test timed out"


@cocotb.test()
def test_falling_edge(dut):
    """Test that a falling edge can be yielded on"""
    dut.clk <= 1
    yield Timer(1)
    test = cocotb.fork(do_single_edge_check(dut, 0))
    yield Timer(10)
    dut.clk <= 0
    fail_timer = Timer(1000)
    result = yield [fail_timer, test.join()]
    assert result is not fail_timer, "Test timed out"


@cocotb.test()
def test_either_edge(dut):
    """Test that either edge can be triggered on"""
    dut.clk <= 0
    yield Timer(1)
    dut.clk <= 1
    yield Edge(dut.clk)
    assert dut.clk.value.integer == 1
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    assert dut.clk.value.integer == 0
    yield Timer(10)
    dut.clk <= 1
    yield Edge(dut.clk)
    assert dut.clk.value.integer == 1
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    assert dut.clk.value.integer == 0
    yield Timer(10)
    dut.clk <= 1
    yield Edge(dut.clk)
    assert dut.clk.value.integer == 1
    yield Timer(10)
    dut.clk <= 0
    yield Edge(dut.clk)
    assert dut.clk.value.integer == 0


@cocotb.test()
def test_fork_and_monitor(dut, period=1000, clocks=6):
    cocotb.fork(Clock(dut.clk, period).start())

    # Ensure the clock has started
    yield RisingEdge(dut.clk)

    timer = Timer(period + 10)
    task = cocotb.fork(count_edges_cycles(dut.clk, clocks))
    count = 0
    expect = clocks - 1

    while True:
        result = yield [timer, task.join()]
        assert count <= expect, "Task didn't complete in expected time"
        if result is timer:
            dut._log.info("Count %d: Task still running" % count)
            count += 1
        else:
            break
    assert count == expect, "Expected to monitor the task %d times but got %d" % (expect, count)
    assert result == clocks, "Expected task to return %d but got %s" % (clocks, repr(result))


@cocotb.coroutine
def do_clock(dut, limit, period):
    """Simple clock with a limit"""
    wait_period = period / 2
    while limit:
        yield Timer(wait_period)
        dut.clk <= 0
        yield Timer(wait_period)
        dut.clk <= 1
        limit -= 1


@cocotb.coroutine
def do_edge_count(dut, signal):
    """Count the edges"""
    global edges_seen
    count = 0
    while True:
        yield RisingEdge(signal)
        edges_seen += 1


@cocotb.test()
def test_edge_count(dut):
    """Count the number of edges is as expected"""
    global edges_seen
    edges_seen = 0
    clk_period = 100
    edge_count = 10
    clock = cocotb.fork(do_clock(dut, edge_count, clk_period))
    test = cocotb.fork(do_edge_count(dut, dut.clk))

    yield Timer(clk_period * (edge_count + 1))

    assert edge_count == edges_seen, "Correct edge count failed - saw %d, wanted %d" % (edges_seen, edge_count)


@cocotb.test()
def test_edge_identity(dut):
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
    yield Timer(1)


@cocotb.test()
def test_singleton_isinstance(dut):
    """
    Test that the result of trigger expression have a predictable type
    """
    assert isinstance(RisingEdge(dut.clk), RisingEdge)
    assert isinstance(FallingEdge(dut.clk), FallingEdge)
    assert isinstance(Edge(dut.clk), Edge)

    yield Timer(1)


@cocotb.test()
def test_clock_cycles(dut):
    """
    Test the ClockCycles Trigger
    """

    clk = dut.clk

    clk_gen = cocotb.fork(Clock(clk, 100).start())

    yield RisingEdge(clk)

    dut._log.info("After one edge")

    yield ClockCycles(clk, 10)

    dut._log.info("After 10 edges")


@cocotb.test()
def test_clock_cycles_forked(dut):
    """ Test that ClockCycles can be used in forked coroutines """
    # gh-520

    clk_gen = cocotb.fork(Clock(dut.clk, 100).start())

    @cocotb.coroutine
    def wait_ten():
        yield ClockCycles(dut.clk, 10)

    a = cocotb.fork(wait_ten())
    b = cocotb.fork(wait_ten())
    yield a.join()
    yield b.join()
