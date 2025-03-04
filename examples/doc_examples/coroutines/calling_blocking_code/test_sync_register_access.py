# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

# test_sync_register_access.py

import random

import cocotb
from cocotb.triggers import Timer
from cocotb.clock import Clock


async def async_read(dut):
    """Read the register of the DUT."""

    return dut.register_out.value

async def async_write(dut, value):
    """Write the register of the DUT."""

    dut.write_enable.value = 1
    dut.register_in.value = value
    await Timer(2, units="ns")  # wait at least one clock period
    dut.write_enable.value = 0

def sync_read(dut):
    """Go back into the asynchronous context and read the register."""

    return cocotb.resume(async_read)(dut)

def sync_write(dut, value):
    """Go back into the asynchronous context and write the register."""

    return cocotb.resume(async_write)(dut, value)

@cocotb.test()
async def test_synchronous_register_access(dut):
    """Test synchronous register read / write."""

    Clock(dut.clk, 1, units="ns").start()

    write = random.randint(1, 256)  # write some other value than the register's initial value
    await cocotb.bridge(sync_write)(dut, write)  # call synchronous function by using bridge()
    await Timer(2, units="ns")  # wait for the output of the register to toggle
    result = await cocotb.bridge(sync_read)(dut)
    assert write == result, f"read value {result} is not the written value {write}!"
