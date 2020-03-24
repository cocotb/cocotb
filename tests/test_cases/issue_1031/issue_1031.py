# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from cocotb import test, fork
from cocotb.triggers import Lock, Timer

@test()
async def test_trigger_lock(dut):
    """
    Simple test that checks to see if context management is kept. The
    resource value is checked at certain points if it equals the expected
    amount, which is easily predictable if the context management is working.
    """
    resource = [0]
    lock = Lock()

    fork(co(resource, lock))
    async with lock:
        for i in range(4):
            resource[0] += 1
            await Timer(10, "ns")
    assert resource[0]==4
    await Timer(10, "ns")
    async with lock:
        assert resource[0]==8

async def co(resource, lock):
    await Timer(10, "ns")
    async with lock:
        for i in range(4):
            resource[0] += 1
            await Timer(10, "ns")


@test(timeout_time=100, timeout_unit="ns")
async def test_except_lock(dut):
    """
    Checks to see if exceptions cause the lock to be
    released.
    """
    lock = Lock()
    try:
        async with lock:
            assert False
    except AssertionError:
        pass
    async with lock:
        assert True
