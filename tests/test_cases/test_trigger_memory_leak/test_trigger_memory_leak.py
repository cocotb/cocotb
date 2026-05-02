# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests related to timing triggers

* Timer
* ReadWrite
* ReadOnly
* NextTimeStep
* RisingEdge
* FallingEdge
* NullTrigger
* ValueChange
* Event
"""

from __future__ import annotations

import gc
import os

import psutil

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import (
    Event,
    FallingEdge,
    NextTimeStep,
    NullTrigger,
    ReadOnly,
    ReadWrite,
    RisingEdge,
    Timer,
    ValueChange,
)

SIM_NAME = cocotb.SIM_NAME.lower()
proc = psutil.Process(os.getpid())
# diff less than n * 4k for ASLR, if use THP, maybe lessthan n * 2MB
MEMORY_LEAK_TH = 2**23 if SIM_NAME.startswith("modelsim") else 2**21


@cocotb.test(skip=(SIM_NAME.startswith("modelsim")))
async def test_next_time_step_leak(dut):
    clk = Clock(dut.clk, 1, "ns")
    cocotb.start_soon(clk.start())
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await NextTimeStep()
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_timer_leak(dut):
    await Timer(1_000, unit="ns")
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await Timer(1, unit="ns")
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_readonly_leak(dut):
    await Timer(1_000, unit="ns")
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await ReadOnly()
        await Timer(1, unit="ns")
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_readwrite_leak(dut):
    await Timer(1_000, unit="ns")
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await Timer(1, unit="ns")
        await ReadWrite()

    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_raise_edge_leak(dut):
    clk = Clock(dut.clk, 1, "ns")
    cocotb.start_soon(clk.start())
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await RisingEdge(dut.clk)
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_falling_edge_leak(dut):
    clk = Clock(dut.clk, 1, "ns")
    cocotb.start_soon(clk.start())
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await FallingEdge(dut.clk)
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_value_change_leak(dut):
    clk = Clock(dut.clk, 1, "ns")
    cocotb.start_soon(clk.start())
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await ValueChange(dut.clk)
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_null_triger_leak(dut):
    await Timer(1_000, unit="ns")
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        await NullTrigger()
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"


@cocotb.test()
async def test_event_leak(dut):
    e = Event()

    async def wait_event() -> None:
        for _ in range(100_000):
            await e.wait()

    cocotb.start_soon(wait_event())

    await Timer(1_000, unit="ns")
    rss_start = proc.memory_info().rss
    await Timer(100_000, unit="ns")
    rss_no_triger = proc.memory_info().rss
    for _ in range(100_000):
        e.set()
        await Timer(1, "ns")
    gc.collect()
    rss_triger = proc.memory_info().rss
    diff = rss_triger - rss_no_triger - rss_no_triger + rss_start
    assert diff <= MEMORY_LEAK_TH, "Memory leak"
