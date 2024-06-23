# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import os

import cocotb
from cocotb._conf import trust_inertial
from cocotb.clock import Clock
from cocotb.result import SimTimeoutError
from cocotb.triggers import ReadOnly, ReadWrite, RisingEdge, Timer, with_timeout

SIM_NAME = cocotb.SIM_NAME.lower()
vhdl = os.environ.get("TOPLEVEL_LANG", "verilog").lower() == "vhdl"
verilog = os.environ.get("TOPLEVEL_LANG", "verilog").lower() == "verilog"

simulator_test = "COCOTB_SIMULATOR_TEST" in os.environ

# Riviera's VHPI is skipped in all tests when COCOTB_TRUST_INERTIAL_WRITES mode is enabled
# because it behaves erratically.
riviera_vhpi_trust_inertial = SIM_NAME.startswith("riviera") and vhdl and trust_inertial


# Verilator < v5.026 only does vpiNoDelay writes.
@cocotb.test(
    expect_error=SimTimeoutError
    if (SIM_NAME.startswith("verilator") and trust_inertial)
    else (),
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
elif trust_inertial:
    expect_fail = False
elif SIM_NAME.startswith(("riviera", "modelsim")) and vhdl:
    expect_fail = False
elif SIM_NAME.startswith("verilator"):
    expect_fail = False
else:
    expect_fail = True


# Verilator < v5.026 only does vpiNoDelay writes, so this works.
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

    # write in the "normal" phase
    dut.clk.value = 1

    # assert we can read back what we wrote in the ReadWrite phase
    await ReadWrite()
    assert dut.clk.value == 1


if simulator_test:
    expect_fail = False
elif not trust_inertial:
    expect_fail = False
elif SIM_NAME.startswith(("icarus", "verilator")):
    expect_fail = True
elif SIM_NAME.startswith("modelsim") and verilog:
    expect_fail = True
elif SIM_NAME.startswith("xmsim") and vhdl:
    expect_fail = True


# Verilator < v5.026 only does vpiNoDelay writes.
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
