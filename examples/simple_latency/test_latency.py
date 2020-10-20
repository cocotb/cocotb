# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Edge
from cocotb.clock import Timer


async def delayed_wire (output_sig, input_sig, latency):
    while (1):
        await Edge(input_sig)
        cocotb.fork(delayer(output_sig, input_sig.value, latency))


async def delayer(output_sig, val, latency, unit="us"):
    await Timer(latency, units=unit)
    output_sig <= val


@cocotb.test()
async def test_dff_simple(dut):
    """ Test that d propagates to q """

    clock = Clock(dut.clk, 10, units="us")  # Create a 10us period clock on port clk
    cocotb.fork(clock.start())  # Start the clock
    cocotb.fork(delayed_wire(dut.delayed_d[0], dut.q, 2))
    cocotb.fork(delayed_wire(dut.delayed_d[1], dut.q, 8))
    cocotb.fork(delayed_wire(dut.delayed_d[2], dut.q, 14))

    await FallingEdge(dut.clk)  # Synchronize with the clock

    # To hold singal value during two previous clock
    old_val1 = 0
    old_val2 = 0

    for i in range(20):
        val = random.randint(0, 1)
        dut.d <= val  # Assign the random value val to the input port d
        await FallingEdge(dut.clk)
        assert dut.q == val, "output q was incorrect on the {}th cycle".format(i)

        # check output of delayed signals
        if (dut.delayed_q[0].value): # Avoid X/Z, expected 1 cycle delay
            assert dut.delayed_q[0] == old_val1, "output delayed_q[0] was incorrect on the {}th cycle".format(i)
        if (dut.delayed_q[1].value): # Avoid X/Z, expected 1 cycle delay
            assert dut.delayed_q[1] == old_val1, "output delayed_q[1] was incorrect on the {}th cycle".format(i)
        if (dut.delayed_q[2].value): # Avoid X/Z, expected 2 cycles delay
            assert dut.delayed_q[2] == old_val2, "output delayed_q[2] was incorrect on the {}th cycle".format(i)

        # update value of previous cycle signal
        old_val2 = old_val1
        old_val1 = val
