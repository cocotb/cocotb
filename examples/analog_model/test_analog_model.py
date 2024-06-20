# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

from afe import AFE

import cocotb
from cocotb.clock import Clock
from cocotb.queue import Queue
from cocotb.triggers import Edge, RisingEdge, Timer

"""
This example uses the Python model of an Analog Front-End (AFE)
which contains a Programmable Gain Amplifier (PGA)
and an Analog-to-Digital Converter (ADC).

The digital part (in HDL) monitors the measurement value converted by the ADC
and selects the gain of the PGA based on the received value.
"""


async def gain_select(digital, afe) -> None:
    """Set gain factor of PGA when gain select from the HDL changes."""

    while True:
        await Edge(digital.pga_high_gain)
        if digital.pga_high_gain.value == 0:
            afe.pga.gain = 5.0
        else:
            afe.pga.gain = 10.0


@cocotb.test()
async def test_analog_model(digital) -> None:
    """Exercise an Analog Front-end and its digital controller."""

    clock = Clock(digital.clk, 1, units="us")  # create a 1us period clock on port clk
    cocotb.start_soon(clock.start())  # start the clock

    afe_in_queue = Queue()
    afe_out_queue = Queue()
    afe = AFE(
        in_queue=afe_in_queue, out_queue=afe_out_queue
    )  # instantiate the analog front-end

    cocotb.start_soon(gain_select(digital, afe))

    for in_V in [0.1, 0.1, 0.0, 0.25, 0.25]:
        # set the input voltage
        await afe_in_queue.put(in_V)

        # get the converted digital value
        afe_out = await afe_out_queue.get()

        digital._log.info(f"AFE converted input value {in_V}V to {int(afe_out)}")

        # hand digital value over as "meas_val" to digital part (HDL)
        # "meas_val_valid" pulses for one clock cycle
        await RisingEdge(digital.clk)
        digital.meas_val.value = afe_out
        digital.meas_val_valid.value = 1
        await RisingEdge(digital.clk)
        digital.meas_val_valid.value = 0
        await Timer(3.3, "us")
