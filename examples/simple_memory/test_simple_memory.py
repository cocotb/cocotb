# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
"""Cocotb tests for ``simple_memory`` — a tiny multi-bank synchronous DRAM-style DUT.

Demonstrates the verification patterns a real DRAM controller exercises:

* per-bank ACT / PRE / RD / WR state machine
* ACT-before-RD/WR ordering (RD/WR to an Idle bank returns no data)
* all-bank REFAB resets every bank to Idle
* a small golden model that mirrors the DUT and checks every read

Together these are the smallest set of behaviours that distinguish a
multi-bank DRAM-style memory from a flat single-port RAM.
"""
from __future__ import annotations

import os
import random
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb_tools.runner import get_runner

# Command encoding — must match simple_memory.sv
CMD_NOP, CMD_ACT, CMD_PRE, CMD_RD, CMD_WR, CMD_REFAB = range(6)

N_BANKS = 4
ROW_BITS = 4
COL_BITS = 4
N_ROWS = 1 << ROW_BITS
N_COLS = 1 << COL_BITS


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


@cocotb.test()
async def single_bank_write_read(dut):
    """Write a row through one bank, read it back, verify."""
    Clock(dut.clk, 10, unit="ns").start(start_high=False)
    await _reset(dut)

    bank, row = 1, 5
    pattern = [0xCAFE_0000 | (i * 0x11) for i in range(8)]

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
async def rd_from_idle_bank_returns_no_data(dut):
    """JEDEC-style ordering: RD without a prior ACT must not assert rdata_valid."""
    Clock(dut.clk, 10, unit="ns").start(start_high=False)
    await _reset(dut)

    # No ACT first — bank stays Idle.
    await _send(dut, CMD_RD, bank=2, addr=0)
    await RisingEdge(dut.clk)
    assert int(dut.rdata_valid.value) == 0, (
        "rdata_valid asserted on RD from Idle bank — DUT must gate on bank_state"
    )


@cocotb.test()
async def refab_returns_all_banks_to_idle(dut):
    """After REFAB, every bank must be Idle — confirmed by a follow-up RD
    that should NOT see rdata_valid (because no ACT was reissued)."""
    Clock(dut.clk, 10, unit="ns").start(start_high=False)
    await _reset(dut)

    # Open three banks, write a beat into each.
    for bank in (0, 1, 3):
        await _send(dut, CMD_ACT, bank=bank, addr=bank + 1)
        await _send(dut, CMD_WR, bank=bank, addr=0, wdata=0xDEAD_0000 | bank)

    # All-bank refresh — every bank back to Idle.
    await _send(dut, CMD_REFAB)
    await _nop(dut)

    # Without a fresh ACT, RD must not return data.
    for bank in (0, 1, 3):
        await _send(dut, CMD_RD, bank=bank, addr=0)
        await RisingEdge(dut.clk)
        assert int(dut.rdata_valid.value) == 0, (
            f"bank {bank} not Idle after REFAB — DUT must close every bank"
        )


@cocotb.test()
async def random_traffic_with_golden_model(dut):
    """200 random ACT/PRE/RD/WR shots across all banks, checked against an
    in-Python golden model that mirrors the bank state and memory contents."""
    Clock(dut.clk, 10, unit="ns").start(start_high=False)
    await _reset(dut)

    # Golden model: per-bank (open_row, dict of col -> data) plus an Idle flag.
    bank_state = ["IDLE"] * N_BANKS
    bank_open_row = [None] * N_BANKS
    mem = [[[0] * N_COLS for _ in range(N_ROWS)] for _ in range(N_BANKS)]

    rng = random.Random(0xC0C07B)   # fixed seed → reproducible across cocotb versions
    n_reads = 0
    n_writes = 0

    for _ in range(200):
        bank = rng.randint(0, N_BANKS - 1)
        choice = rng.random()

        if choice < 0.25 or bank_state[bank] == "IDLE":
            # ACT (also forced when bank is Idle and the random pick wanted RD/WR).
            row = rng.randint(0, N_ROWS - 1)
            await _send(dut, CMD_ACT, bank=bank, addr=row)
            bank_state[bank] = "ACTIVE"
            bank_open_row[bank] = row
        elif choice < 0.40:
            # PRE
            await _send(dut, CMD_PRE, bank=bank)
            bank_state[bank] = "IDLE"
            bank_open_row[bank] = None
        elif choice < 0.70:
            # WR
            col = rng.randint(0, N_COLS - 1)
            data = rng.randint(0, 0xFFFF_FFFF)
            await _send(dut, CMD_WR, bank=bank, addr=col, wdata=data)
            mem[bank][bank_open_row[bank]][col] = data
            n_writes += 1
        else:
            # RD
            col = rng.randint(0, N_COLS - 1)
            expected = mem[bank][bank_open_row[bank]][col]
            await _send(dut, CMD_RD, bank=bank, addr=col)
            await RisingEdge(dut.clk)
            assert int(dut.rdata_valid.value) == 1, (
                f"rdata_valid not asserted on RD bank={bank} col={col}"
            )
            got = int(dut.rdata.value)
            assert got == expected, (
                f"mismatch bank={bank} row={bank_open_row[bank]} col={col}: "
                f"got 0x{got:08x} exp 0x{expected:08x}"
            )
            n_reads += 1

    # Ensure the random mix actually exercised both paths.
    assert n_writes > 10, f"random mix did not hit enough WRs ({n_writes})"
    assert n_reads > 10, f"random mix did not hit enough RDs ({n_reads})"


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
