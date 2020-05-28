# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for synchronization primitives like Lock and Event
"""
import cocotb
from cocotb.triggers import Lock, Timer


@cocotb.test()
async def test_trigger_lock(dut):
    """
    Simple test that checks to see if context management is kept. The
    resource value is checked at certain points if it equals the expected
    amount, which is easily predictable if the context management is working.
    """
    resource = 0
    lock = Lock()

    async def co():
        nonlocal resource
        await Timer(10, "ns")
        async with lock:
            for i in range(4):
                await Timer(10, "ns")
                resource += 1

    cocotb.fork(co())
    async with lock:
        for i in range(4):
            resource += 1
            await Timer(10, "ns")
    assert resource == 4
    await Timer(10, "ns")
    async with lock:
        assert resource == 8


@cocotb.test(timeout_time=100, timeout_unit="ns")
async def test_except_lock(dut):
    """
    Checks to see if exceptions cause the lock to be
    released.
    """
    lock = Lock()
    try:
        async with lock:
            raise RuntimeError()
    except RuntimeError:
        pass
    async with lock:
        pass
