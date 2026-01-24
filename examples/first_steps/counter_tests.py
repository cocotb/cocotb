# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
# ruff: noqa: F841
# fmt: off
from __future__ import annotations

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


# test_hello_world
@cocotb.test
async def test_hello_world(dut):
    cocotb.log.info("Hello, World!")
# end test_hello_world

# test_accessing
@cocotb.test
async def test_accessing(dut):
    # Gets a reference to the 'clk' object
    handle_to_clk = dut.clk
# end test_accessing

# test_getting_setting_values
@cocotb.test
async def test_getting_values(dut):
    cocotb.log.info("Current clk value is %r", dut.clk.value)
    # Will print `Current clk value is Logic('X')`
    cocotb.log.info("Current din value is %r", dut.din.value)
    # Will print `Current din value is LogicArray('XXXXXXXX', Range(7, 'downto', 0))`

    dut.clk.value = 1
    dut.din.value = 124
# end test_getting_setting_values

# test_waiting
@cocotb.test
async def test_waiting(dut):
    dut.clk.value = 1
    dut.din.value = 124

    await Timer(1, "ns")

    cocotb.log.info("Current clk value is %r", dut.clk.value)
    # Will print `Current clk value is Logic('1')`
    cocotb.log.info("Current din value is %r", dut.din.value)
    # Will print `Current din value is LogicArray('01111100', Range(7, 'downto', 0))`
# end test_waiting

# test_clock
@cocotb.test
async def test_clock(dut):
    # Run a clock with a 2 ns period for 20 cycles
    for _ in range(20):
        dut.clk.value = 1
        await Timer(1, "ns")
        dut.clk.value = 0
        await Timer(1, "ns")
# end test_clock

# test_clock_concurrent
@cocotb.test
async def test_clock_concurrent(dut):
    # Start the clock running concurrently to the main test coroutine.
    cocotb.start_soon(run_clock(dut))

    # Do other things in the main test coroutine while the clock is running.
    await Timer(200, "ns")


async def run_clock(dut):
    # Run a clock with a 2 ns period indefinitely.
    while True:
        dut.clk.value = 1
        await Timer(1, "ns")
        dut.clk.value = 0
        await Timer(1, "ns")
# end test_clock_concurrent

# test_edge_trigger
async def reset(dut):
    # Set initial values for the signals.
    dut.ena.value = 0
    dut.rst.value = 0
    dut.set.value = 0
    dut.din.value = 0

    # Keep the reset signal high for 3 clock cycles.
    dut.rst.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0


@cocotb.test
async def test_edge_trigger(dut):
    # Start the clock running concurrently to the main test coroutine
    Clock(dut.clk, 2, "ns").start()

    await reset(dut)

    # Load the counter with the value 10.
    dut.din.value = 10
    dut.set.value = 1
    await RisingEdge(dut.clk)
    dut.set.value = 0

    # Set the enable so the counter will increment the 'count' signal
    # for the next 20 clock cycles.
    dut.ena.value = 1
    for _ in range(20):
        await RisingEdge(dut.clk)
# end test_edge_trigger

# test_self_checking
@cocotb.test
async def test_self_checking(dut):
    # Start the clock running concurrently to the main test coroutine.
    Clock(dut.clk, 10, "ns").start()

    # We are reusing reset() from the previous example.
    await reset(dut)

    # Load the counter with the value 10.
    dut.din.value = 10
    dut.set.value = 1
    await RisingEdge(dut.clk)
    dut.set.value = 0

    # Wait for the quiescent state and ensure our register has updated
    # to the value that was set during the rising edge of the clock.
    await Timer(1, "ns")
    # We expect that the value we loaded earlier is what we read
    # after the next clock edge.
    assert dut.count.value == 10

    # Set the enable so the counter will increment the 'count' signal
    # for the next 20 clock cycles.
    dut.ena.value = 1
    expected_value = 10
    for _ in range(20):
        # On each clock edge we expect that the result increments by 1.
        expected_value += 1
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        assert dut.count.value == expected_value
# end test_self_checking
