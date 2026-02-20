"""Cocotb benchmark: tight signal read/write loop for profiling."""

from __future__ import annotations

import cProfile
import os
import pstats
import time
from pathlib import Path

import cocotb
from cocotb import fast
from cocotb.clock import Clock
from cocotb.fast import SignalProxy, run_cycles
from cocotb.triggers import RisingEdge


def _run_profiler(prof, out_dir):
    """Dump and print cProfile results."""
    prof_path = out_dir / "profile.prof"
    prof.dump_stats(str(prof_path))
    cocotb.log.info(f"Profile saved to {prof_path}")

    stats = pstats.Stats(prof)
    stats.sort_stats("cumulative")
    cocotb.log.info("=== Top 30 by cumulative time ===")
    stats.print_stats(30)

    stats.sort_stats("tottime")
    cocotb.log.info("=== Top 30 by total time ===")
    stats.print_stats(30)


@cocotb.test()
async def bench_signal_rw(dut):
    """Benchmark: rapid signal read/write over many clock cycles."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.stream_in_data.value = 0
    dut.stream_in_valid.value = 0
    dut.stream_out_ready.value = 1

    await RisingEdge(dut.clk)

    N = 1_000_000
    rising = RisingEdge(dut.clk)

    do_profile = os.environ.get("COCOTB_PROFILE", "0") == "1"
    prof = cProfile.Profile() if do_profile else None
    out_dir = Path(__file__).resolve().parent

    if prof:
        prof.enable()

    t0 = time.perf_counter()
    for i in range(N):
        # Write signals
        dut.stream_in_data.value = i & 0xFF
        dut.stream_in_valid.value = 1

        await rising

        # Read signals back
        _ = dut.stream_out_data.value
        _ = dut.stream_in_ready.value

    elapsed = time.perf_counter() - t0
    if prof:
        prof.disable()

    dut.stream_in_valid.value = 0
    await rising

    cocotb.log.info(
        f"[rw] Loop completed: {N} cycles in {elapsed:.2f}s ({N / elapsed:.0f} cycles/s)"
    )

    if prof:
        _run_profiler(prof, out_dir)


@cocotb.test()
async def bench_read_heavy(dut):
    """Benchmark: many reads per clock cycle to isolate read-path overhead."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    dut.stream_in_data.value = 0xAB
    dut.stream_in_valid.value = 1
    dut.stream_out_ready.value = 1
    await RisingEdge(dut.clk)

    N = 200_000
    READS_PER_CYCLE = 20
    rising = RisingEdge(dut.clk)

    t0 = time.perf_counter()
    for _ in range(N):
        for _ in range(READS_PER_CYCLE):
            _ = dut.stream_out_data.value
            _ = dut.stream_in_ready.value
            _ = dut.stream_out_valid.value
        await rising

    elapsed = time.perf_counter() - t0
    total_reads = N * READS_PER_CYCLE * 3
    cocotb.log.info(
        f"[read-heavy] {total_reads / 1e6:.1f}M reads in {elapsed:.2f}s "
        f"({total_reads / elapsed:.0f} reads/s, {N / elapsed:.0f} cycles/s)"
    )


@cocotb.test()
async def bench_write_heavy(dut):
    """Benchmark: many writes per clock cycle to isolate write-path overhead."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    dut.stream_out_ready.value = 1
    await RisingEdge(dut.clk)

    N = 200_000
    WRITES_PER_CYCLE = 20
    rising = RisingEdge(dut.clk)

    t0 = time.perf_counter()
    for i in range(N):
        for j in range(WRITES_PER_CYCLE):
            dut.stream_in_data.value = (i + j) & 0xFF
        await rising

    elapsed = time.perf_counter() - t0
    total_writes = N * WRITES_PER_CYCLE
    cocotb.log.info(
        f"[write-heavy] {total_writes / 1e6:.1f}M writes in {elapsed:.2f}s "
        f"({total_writes / elapsed:.0f} writes/s, {N / elapsed:.0f} cycles/s)"
    )


@cocotb.test()
async def bench_getattr_heavy(dut):
    """Benchmark: repeated attribute lookups to isolate __getattr__ overhead."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    dut.stream_in_data.value = 0
    await RisingEdge(dut.clk)

    N = 200_000
    LOOKUPS_PER_CYCLE = 20
    rising = RisingEdge(dut.clk)

    t0 = time.perf_counter()
    for _ in range(N):
        for _ in range(LOOKUPS_PER_CYCLE):
            _ = dut.stream_out_data
            _ = dut.stream_in_ready
            _ = dut.stream_out_valid
            _ = dut.stream_in_data
        await rising

    elapsed = time.perf_counter() - t0
    total_lookups = N * LOOKUPS_PER_CYCLE * 4
    cocotb.log.info(
        f"[getattr-heavy] {total_lookups / 1e6:.1f}M lookups in {elapsed:.2f}s "
        f"({total_lookups / elapsed:.0f} lookups/s, {N / elapsed:.0f} cycles/s)"
    )


@cocotb.test()
async def bench_fast_loop(dut):
    """Benchmark: fast-loop API — same workload as bench_signal_rw but via run_cycles."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.stream_in_data.value = 0
    dut.stream_in_valid.value = 0
    dut.stream_out_ready.value = 1
    await RisingEdge(dut.clk)

    N = 1_000_000

    # Create lightweight proxies — no Logic/LogicArray per access
    data_in = SignalProxy(dut.stream_in_data)
    valid_in = SignalProxy(dut.stream_in_valid)
    data_out = SignalProxy(dut.stream_out_data)
    ready_in = SignalProxy(dut.stream_in_ready)

    do_profile = os.environ.get("COCOTB_PROFILE", "0") == "1"
    prof = cProfile.Profile() if do_profile else None
    out_dir = Path(__file__).resolve().parent

    if prof:
        prof.enable()

    def step(cycle: int) -> bool:
        # Write signals
        data_in.set_int(cycle & 0xFF)
        valid_in.set_int(1)
        # Read signals back
        _ = data_out.get_int()
        _ = ready_in.get_int()
        return cycle < N - 1

    t0 = time.perf_counter()
    total = await run_cycles(dut.clk, step)
    elapsed = time.perf_counter() - t0

    if prof:
        prof.disable()

    dut.stream_in_valid.value = 0
    await RisingEdge(dut.clk)

    cocotb.log.info(
        f"[fast-loop] Loop completed: {total} cycles in {elapsed:.2f}s "
        f"({total / elapsed:.0f} cycles/s)"
    )

    if prof:
        _run_profiler(prof, out_dir)


@cocotb.test()
async def bench_fast_sched(dut):
    """Benchmark: fast mini-scheduler — async/await style with multiple phases."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.stream_in_data.value = 0
    dut.stream_in_valid.value = 0
    dut.stream_out_ready.value = 1
    await RisingEdge(dut.clk)

    N = 1_000_000

    # Create lightweight proxies
    data_in = fast.SignalProxy(dut.stream_in_data)
    valid_in = fast.SignalProxy(dut.stream_in_valid)
    data_out = fast.SignalProxy(dut.stream_out_data)
    ready_in = fast.SignalProxy(dut.stream_in_ready)

    # Create reusable triggers (allocated once, not per cycle)
    rising = fast.RisingEdge(dut.clk)
    ro = fast.ReadOnly()

    do_profile = os.environ.get("COCOTB_PROFILE", "0") == "1"
    prof = cProfile.Profile() if do_profile else None
    out_dir = Path(__file__).resolve().parent

    if prof:
        prof.enable()

    async def inner():
        for i in range(N):
            # Write signals
            data_in.set_int(i & 0xFF)
            valid_in.set_int(1)
            await rising
            # Read in ReadOnly phase for stable values
            await ro
            _ = data_out.get_int()
            _ = ready_in.get_int()

    t0 = time.perf_counter()
    await fast.run(inner())
    elapsed = time.perf_counter() - t0

    if prof:
        prof.disable()

    dut.stream_in_valid.value = 0
    await RisingEdge(dut.clk)

    cocotb.log.info(
        f"[fast-sched] Loop completed: {N} cycles in {elapsed:.2f}s "
        f"({N / elapsed:.0f} cycles/s)"
    )

    if prof:
        _run_profiler(prof, out_dir)
