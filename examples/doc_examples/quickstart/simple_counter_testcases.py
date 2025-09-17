# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

"""This module contains testcases for the simple_counter"""

# Imports for all Quickstart examples
import cocotb
from cocotb import start_soon
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, NextTimeStep, ReadOnly, RisingEdge, Timer

# QUICKSTART 1


@cocotb.test()
async def quickstart_1(dut):
    """Quickstart Example 1 - Showcasing a single sequential routine

    Keyword arguments:
    dut -- the hdl toplevel
    """

    # Initial value.
    dut.ena.value = 0

    # Reset sequence and clock start.
    dut.rst.value = 1
    input_clock = Clock(dut.clk, 10, unit="ns")
    input_clock.start()
    await Timer(5, "ns")

    # Re-synchronize with the clock
    await RisingEdge(dut.clk)
    dut.rst.value = 0

    # Activating the dut.ena input signal, to enable the counter.
    dut.ena.value = 1

    count_cycles = 10
    for _ in range(count_cycles):
        await RisingEdge(dut.clk)

    # Deactivating the dut.ena input signal, to disable the counter.
    dut.ena.value = 0
    await RisingEdge(dut.clk)
    # Checking that the counter output.
    assert dut.counter.value == count_cycles

    # Wait some time, to let a few clock cycles pass.
    await Timer(100, "ns")

    # Checking that the "counter" output did not increment when ena was inactive.
    assert dut.counter.value == count_cycles


# END QUICKSTART 1

# QUICKSTART 2


async def reset_and_start_clock(reset, clock, cycles=10):
    """Coroutine to active reset, and start a clock

    Activate reset for a few cycles before deactivating and returning
    Signals can be passed as arguments.
    Keyword arguments:
    reset -- the reset signal in the dut
    clock -- the clock signal in the dut
    cycles -- how many cycles to activate reset (default 10)
    """
    reset.value = 1
    input_clock = Clock(clock, 10, unit="ns")
    input_clock.start()
    for _ in range(cycles):
        await RisingEdge(clock)
    reset.value = 0


async def enable_counter(dut, cycles=10):
    """Activate dut.ena for some clock cycles, before deactivating.

    Signals do not have to be passed as arguments.
    Keyword arguments:
    dut -- the hdl toplevel
    cycles -- number of cycles to keep dut.ena high (default 10)
    """
    await FallingEdge(dut.clk)
    dut.ena.value = 1
    for _ in range(cycles):
        await RisingEdge(dut.clk)

    dut.ena.value = 0
    await RisingEdge(dut.clk)


async def check_counter(dut, start_value):
    """A run forever coroutine,  continuously checks the counter on every rising edge of the clock.

    Keyword arguments:
    dut -- the hdl toplevel
    start_value -- the expected value of the counter when this coroutine is started.
    """
    expected_counter_value = start_value
    assert dut.counter.value == expected_counter_value

    while True:
        await RisingEdge(dut.clk)
        if dut.set.value == 1:
            expected_counter_value = dut.din.value
        elif dut.ena.value == 1:
            expected_counter_value += 1

        # Wait for the ReadOnly phase to let delta cycles complete.
        await ReadOnly()  # More about this in Quickstart 3
        assert dut.counter.value == expected_counter_value


@cocotb.test()
async def quickstart_2(dut):
    """Quickstart Example 2 - Showcasing coroutines"""

    # Signals in the dut can be assigned to variables for easier use.
    # Can be useful for more complicated signal names.
    rst = dut.rst
    clk = dut.clk
    # Starting reset sequence and clock
    start_soon(reset_and_start_clock(rst, clk))

    # Wait until the reset is inactive.
    await FallingEdge(rst)

    # Quick check after reset.
    assert dut.counter.value == 0

    # Start the check_counter().
    start_soon(check_counter(dut, start_value=0))

    # Start and wait for completion.
    await start_soon(enable_counter(dut, cycles=10))

    # Wait some time, the dut.ena is inactive at this point.
    await Timer(100, "ns")

    # Enable counting again, the check is still going.
    await start_soon(enable_counter(dut, cycles=10))


# END QUICKSTART 2

# QUICKSTART 3


@cocotb.test()
async def quickstart_3(dut):
    """Quickstart Example 3 - Showcasing reading a signal before assertion"""

    # Same starting sequence as in Quickstart 2.
    rst = dut.rst
    clk = dut.clk
    start_soon(reset_and_start_clock(rst, clk))
    await FallingEdge(rst)

    # Quick check after reset.
    assert dut.counter.value == 0

    # Setting some stimuli on the falling edge.
    input_value = 10
    await FallingEdge(clk)
    dut.set.value = 1
    dut.din.value = input_value

    # Waiting for a rising edge before checking the output.
    await RisingEdge(clk)
    try:
        assert dut.counter.value == input_value, (
            "This looks fine in the waveform, why does this fail?\n"
            "It is asserted to the exact same value that was assigned. Makes no sense?!"
        )
    except AssertionError as e:
        cocotb.log.error(e)
        cocotb.log.warning(
            "It fails because the delta cycles of the simulator did not complete, "
            "use ReadOnly() to let the signals 'stabilize'"
        )
    await ReadOnly()
    assert dut.counter.value == input_value, "Now this should not fail!"
    await NextTimeStep()


# END QUICKSTART 3
