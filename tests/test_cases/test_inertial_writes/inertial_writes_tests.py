# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os

import cocotb
from cocotb.clock import Clock
from cocotb.handle import _trust_inertial
from cocotb.triggers import (
    ReadOnly,
    ReadWrite,
    RisingEdge,
    Timer,
    with_timeout,
)

SIM_NAME = cocotb.SIM_NAME.lower()
vhdl = os.environ.get("TOPLEVEL_LANG", "verilog").lower() == "vhdl"
verilog = os.environ.get("TOPLEVEL_LANG", "verilog").lower() == "verilog"
if verilog:
    intf = "vpi"
elif SIM_NAME.startswith("modelsim"):
    intf = os.environ.get("VHDL_GPI_INTERFACE", "fli").strip()
else:
    intf = "vhpi"

simulator_test = "COCOTB_SIMULATOR_TEST" in os.environ

# Riviera's VHPI is skipped in all tests when COCOTB_TRUST_INERTIAL_WRITES mode is enabled
# because it behaves erratically.
riviera_vhpi_trust_inertial = (
    SIM_NAME.startswith("riviera") and intf == "vhpi" and _trust_inertial
)


@cocotb.test(
    skip=riviera_vhpi_trust_inertial and not simulator_test,
)
async def test_writes_on_timer_seen_on_edge(dut):
    # steady state
    dut.clk.value = 0
    await Timer(10, "ns")

    # inertial write on a signal
    dut.clk.value = 1

    # check we can register an edge trigger on the signal we just changed because it hasn't taken effect yet
    await with_timeout(RisingEdge(dut.clk), 10, "ns")


if simulator_test:
    expect_fail = False
elif _trust_inertial:
    expect_fail = False
elif SIM_NAME.startswith("riviera") and intf == "vhpi":
    expect_fail = False
elif SIM_NAME.startswith("modelsim") and intf in ("vhpi", "fli"):
    expect_fail = False
else:
    expect_fail = True


# Riviera and Questa on VHDL designs seem to apply inertial writes in this state immediately,
# presumably because it's the NBA application region.
# This test will fail because the ReadWrite write applicator task does inertial writes of its own.
@cocotb.test(
    expect_fail=expect_fail,
    skip=riviera_vhpi_trust_inertial and not simulator_test,
)
async def test_read_back_in_readwrite(dut):
    # steady state
    dut.clk.value = 0
    await Timer(10, "ns")
    assert dut.clk.value == 0

    # write in the "normal" phase
    dut.clk.value = 1

    # assert we can read back what we wrote in the ReadWrite phase
    await ReadWrite()
    assert dut.clk.value == 1


if simulator_test:
    expect_fail = False
elif not _trust_inertial:
    expect_fail = False
elif SIM_NAME.startswith("icarus"):
    expect_fail = True
elif SIM_NAME.startswith("modelsim") and verilog:
    expect_fail = True
elif SIM_NAME.startswith("xmsim") and intf == "vhpi":
    expect_fail = True
elif "vcs" in SIM_NAME:
    expect_fail = True


# Icarus, Questa VPI, and Xcelium VHPI inertial writes aren't actually inertial.
@cocotb.test(
    expect_fail=expect_fail,
    skip=riviera_vhpi_trust_inertial and not simulator_test,
)
async def test_writes_dont_update_hdl_this_delta(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())

    # assert steady state
    dut.stream_in_data.value = 0
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.stream_out_data_registered.value == 0

    # write on the clock edge
    await RisingEdge(dut.clk)
    dut.stream_in_data.value = 1

    # ensure that the write data wasn't used on this clock cycle
    await ReadOnly()
    assert dut.stream_out_data_registered.value == 0

    # ensure that the write data made it on the result of the next clock cycle
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert dut.stream_out_data_registered.value == 1


@cocotb.test
async def test_writes_in_read_write(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 0
    await RisingEdge(dut.clk)
    assert dut.stream_in_data.value == 0

    # Schedule a write now so the upcoming ReadWrite has a following ReadWrite phase
    # due to writes being scheduled.
    dut.stream_in_data.value = 5

    await ReadWrite()
    # Do a write in the ReadWrite phase to see if it causes issues.
    dut.stream_in_data.value = 1

    await ReadOnly()
    # Was the write applied?
    assert dut.stream_in_data.value == 1


@cocotb.test
async def test_writes_in_last_read_write(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.stream_in_data.value = 0
    await RisingEdge(dut.clk)
    assert dut.stream_in_data.value == 0

    await ReadWrite()
    dut.stream_in_data.value = 1
    # We are now in a ReadWrite phase where no writes have been applied.
    # The simulator may accurately assess that we are at the end of the evaluation loop,
    # as there are no more writes scheduled that it can see (only in cocotb).
    # The above write in COCOTB_TRUST_INERTIAL_WRITES=0 mode will be scheduled for the
    # next ReadWrite phase, which may never come.

    await ReadOnly()
    # Was the write applied?
    assert dut.stream_in_data.value == 1
