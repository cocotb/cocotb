# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for synchronization primitives like Lock and Event
"""

import re

import pytest

import cocotb
from cocotb.triggers import Lock, NullTrigger, Timer, _InternalEvent
from cocotb.utils import get_sim_time


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

    cocotb.start_soon(co())
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


@cocotb.test()
async def test_lock_release_without_acquire(_):
    """Test that Lock will error when released without first being acquired."""
    lock = Lock()
    with pytest.raises(RuntimeError):
        lock.release()


@cocotb.test()
async def test_lock_repr(dut):
    lock = Lock()

    assert re.match(r"<Lock \[0 waiting\] at \w+>", repr(lock))

    lock = Lock(name="my_lock")

    async def task():
        async with lock:
            await Timer(1, "ns")

    for _ in range(3):
        cocotb.start_soon(task())

    assert not lock.locked()

    await NullTrigger()

    assert re.match(r"<Lock for my_lock \[2 waiting\] at \w+>", repr(lock))

    assert lock.locked()

    l = lock.acquire()

    assert re.match(
        r"<<Lock for my_lock \[2 waiting\] at \w+>\.acquire\(\) at \w+>", repr(l)
    )

    await l


@cocotb.test()
async def test_internalevent(dut):
    """Test _InternalEvent trigger."""
    e = _InternalEvent("test parent")
    assert repr(e) == "'test parent'"

    async def set_internalevent():
        await Timer(1, units="ns")
        e.set()

    # Test waiting more than once
    cocotb.start_soon(set_internalevent())
    time_ns = get_sim_time(units="ns")
    await e
    assert e.is_set()
    assert get_sim_time(units="ns") == time_ns + 1
    # _InternalEvent can only be awaited once
    with pytest.raises(RuntimeError):
        await e

    e = _InternalEvent(None)
    assert repr(e) == "None"
    ran = False

    async def await_internalevent():
        nonlocal ran
        await e
        ran = True

    # Test multiple coroutines waiting
    await cocotb.start(await_internalevent())
    assert not e.is_set()
    assert not ran
    # _InternalEvent can only be awaited by one coroutine
    with pytest.raises(RuntimeError):
        await e
    e.set()
    await Timer(1)
    assert e.is_set()
    assert ran

    # Test waiting after set
    e = _InternalEvent(None)
    assert not e.is_set()
    cocotb.start_soon(set_internalevent())
    await Timer(2, units="ns")
    assert e.is_set()
    time_ns = get_sim_time(units="ns")
    await e
    assert get_sim_time(units="ns") == time_ns
