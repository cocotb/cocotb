# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import random

import cocotb
from cocotb.triggers import Timer


async def task_resident(period_ns: int) -> None:
    while True:
        await Timer(period_ns, "ns")


async def task_transient(steps: int) -> None:
    for _ in range(steps):
        await Timer(1, "ns")


async def task_sleep_then_done(delay_ns: int) -> None:
    # Single await then completion, for when only the removal time matters and
    # not how many ticks the task spans.
    await Timer(delay_ns, "ns")


@cocotb.test()
async def typical(dut) -> None:
    # A workload typical of cocotb. A modest number of tasks live for the whole
    # test (resident) plus repeated waves of short lived tasks (transients).
    resident_tasks = 24
    transient_tasks = 24
    waves_tasks = 32

    residents = [cocotb.start_soon(task_resident(5)) for _ in range(resident_tasks)]

    for _ in range(waves_tasks):
        for _ in range(transient_tasks):
            cocotb.start_soon(task_transient(2))
        await Timer(3, "ns")

    for task in residents:
        task.kill()


@cocotb.test()
async def churn_random(dut) -> None:
    # Many tasks completing at random times so removals are interleaved across
    # many scheduler ticks - the removal-sensitive probe for the fix.
    rng = random.Random(0x1234)

    for _ in range(100000):
        cocotb.start_soon(task_sleep_then_done(rng.randint(1, 10000)))

    # Wait for worst case time + 1 for all jobs to finish.
    await Timer(10001, "ns")


@cocotb.test()
async def resident_bulk(dut) -> None:
    # A large resident population started at time 0 and torn down at test end.
    residents = [cocotb.start_soon(task_resident(10000)) for _ in range(500000)]
    await Timer(1, "ns")
    for task in residents:
        task.kill()


@cocotb.test()
async def completion_storm(dut) -> None:
    # Every task completes on the same first tick, so all removals fire in one
    # scheduler step.
    for _ in range(500000):
        cocotb.start_soon(task_transient(1))
    await Timer(2, "ns")


@cocotb.test()
async def fanout(dut) -> None:
    async def parent() -> None:
        for _ in range(50):
            cocotb.start_soon(task_transient(1))
            await Timer(1, "ns")

    parents = [cocotb.start_soon(parent()) for _ in range(1000)]

    await Timer(51, "ns")

    for task in parents:
        task.kill()
