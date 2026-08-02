# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
"""Cocotb tests for ``simple_memory`` — a tiny multi-bank synchronous memory.

This example demonstrates :func:`cocotb.parametrize`. A single write/read test
is expanded into several named tests using grouped bank, row, and data-pattern
parameters. Grouping the parameters makes each tuple one deliberate test case
instead of generating their Cartesian product.

It also shows how :class:`cocotb.triggers.First` can race a read response
against reset, how :func:`cocotb.triggers.with_timeout` bounds that wait, and
how to cancel the task waiting for the event that did not occur.
"""

from __future__ import annotations

import os
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, First, RisingEdge, with_timeout
from cocotb_tools.runner import get_runner

# Command encoding — must match simple_memory.sv
CMD_NOP, CMD_ACT, CMD_PRE, CMD_RD, CMD_WR, CMD_REFAB = range(6)


async def _nop(dut):
    """Drive one cycle of NOP — bus quiet."""
    dut.cmd.value = CMD_NOP
    dut.ba.value = 0
    dut.addr.value = 0
    dut.wdata.value = 0
    await RisingEdge(dut.clk)


async def _send(dut, cmd, bank=0, addr=0, wdata=0):
    """Drive a single-cycle command."""
    dut.cmd.value = cmd
    dut.ba.value = bank
    dut.addr.value = addr
    dut.wdata.value = wdata
    await RisingEdge(dut.clk)


async def _reset(dut):
    """Pulse rst_n low for a few cycles, then release."""
    dut.rst_n.value = 0
    await _nop(dut)
    await _nop(dut)
    dut.rst_n.value = 1
    await _nop(dut)


async def _wait_for_response_or_reset(dut):
    """Wait for a read response or reset, but never wait indefinitely."""

    async def wait_for(trigger):
        await trigger

    response = cocotb.start_soon(wait_for(RisingEdge(dut.rdata_valid)))
    reset = cocotb.start_soon(wait_for(FallingEdge(dut.rst_n)))

    try:
        winner = await with_timeout(First(response.complete, reset.complete), 100, "ns")
        return "response" if winner is response.complete else "reset"
    finally:
        # First() leaves the losing task running, so cancel it explicitly.
        for task in (response, reset):
            if not task.done():
                task.cancel()


@cocotb.test()
@cocotb.parametrize(
    (
        ("bank", "row", "pattern"),
        [
            (0, 0, [0x0000_0000, 0xFFFF_FFFF]),
            (1, 5, [0xCAFE_0000, 0xCAFE_0011]),
            (3, 15, [0x5555_5555, 0xAAAA_AAAA]),
        ],
    )
)
async def write_read(dut, bank, row, pattern):
    """Write a pattern to a selected bank and row, then read it back."""
    Clock(dut.clk, 10, unit="ns").start(start_high=False)
    await _reset(dut)

    await _send(dut, CMD_ACT, bank=bank, addr=row)
    for col, w in enumerate(pattern):
        await _send(dut, CMD_WR, bank=bank, addr=col, wdata=w)

    for col, expected in enumerate(pattern):
        await _send(dut, CMD_RD, bank=bank, addr=col)
        # RD fires combinationally relative to the rising edge; one extra
        # cycle of latency on rdata_valid in this DUT.
        await RisingEdge(dut.clk)
        assert int(dut.rdata_valid.value) == 1, f"rdata_valid not asserted on col {col}"
        got = int(dut.rdata.value)
        assert got == expected, f"col {col}: got 0x{got:08x} exp 0x{expected:08x}"

    await _send(dut, CMD_PRE, bank=bank)


@cocotb.test()
async def read_response_or_reset(dut):
    """Race a read response against reset with a bounded wait."""
    Clock(dut.clk, 10, unit="ns").start(start_high=False)
    await _reset(dut)

    # A normal read completes the response side of First().
    await _send(dut, CMD_ACT, bank=0, addr=0)
    response_or_reset = cocotb.start_soon(_wait_for_response_or_reset(dut))
    await _send(dut, CMD_RD, bank=0, addr=0)
    assert await response_or_reset == "response"

    # While waiting for another response, reset wins instead. The helper
    # cancels the unfinished response task before returning.
    await _nop(dut)
    response_or_reset = cocotb.start_soon(_wait_for_response_or_reset(dut))
    dut.rst_n.value = 0
    assert await response_or_reset == "reset"


def test_simple_memory_runner():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent

    runner = get_runner(sim)
    runner.build(
        sources=[proj_path / "simple_memory.sv"],
        hdl_toplevel="simple_memory",
        always=True,
    )
    runner.test(hdl_toplevel="simple_memory", test_module="test_simple_memory")


if __name__ == "__main__":
    test_simple_memory_runner()
