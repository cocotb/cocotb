# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
from __future__ import annotations

import os
from pathlib import Path

import cocotb
from cocotb.handle import Force, Freeze, Release
from cocotb.triggers import Timer
from cocotb_tools.runner import get_runner

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.getenv("TOPLEVEL_LANG", "verilog").lower().strip()


@cocotb.test
async def tri_state_bus(dut):
    """Show what a deposit, a force and a freeze do to a tri-state bus."""

    # Nothing drives the bus, so it reads as high impedance.
    dut.drive_en.value = 0
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "ZZZZZZZZ"
    assert not dut.data_bus.value.is_resolvable

    # The DUT drives the bus.
    dut.data_out.value = 0xA5
    dut.drive_en.value = 1
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "10100101"

    # A force wins over the value the DUT drives.
    dut.data_bus.value = Force(0x5A)
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "01011010"

    # Releasing brings the value the DUT drives back.
    dut.data_bus.value = Release()
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "10100101"

    # A freeze holds the current value even though the DUT changes what it drives.
    dut.data_bus.value = Freeze()
    dut.data_out.value = 0x3C
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "10100101"
    dut.data_bus.value = Release()

    # With the DUT no longer driving, a plain deposit is what the bus reads back: written from
    # cocotb, but not connected as another driver, so no release is needed afterwards.
    dut.drive_en.value = 0
    await Timer(1, unit="ns")
    dut.data_bus.value = 0xFF
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "11111111"

    # The next deposit simply replaces it.
    dut.data_bus.value = 0x00
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "00000000"

    # And once the DUT drives the bus again the deposit is gone.
    dut.data_out.value = 0x0F
    dut.drive_en.value = 1
    await Timer(1, unit="ns")
    assert dut.data_bus.value == "00001111"
