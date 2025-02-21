# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for synchronization primitives like Lock and Event
"""

import random
import re
from typing import Any, List

import pytest
from common import MyException, assert_takes

import cocotb
from cocotb._base_triggers import Trigger, _InternalEvent
from cocotb.task import Task
from cocotb.triggers import (
    Combine,
    Event,
    First,
    Lock,
    NullTrigger,
    ReadOnly,
    Timer,
)


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
        await Timer(1, unit="ns")
        e.set()

    # Test waiting more than once
    cocotb.start_soon(set_internalevent())
    with assert_takes(1, "ns"):
        await e
    assert e.is_set()
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
    cocotb.start_soon(await_internalevent())
    await NullTrigger()
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
    await Timer(2, unit="ns")
    assert e.is_set()
    with assert_takes(0, "ns"):
        await e


@cocotb.test
async def test_Combine_empty(_) -> None:
    """Test that a Combine with no triggers passes no time."""
    combine = Combine()
    with assert_takes(0, "ns"):
        res = await combine
    assert res is combine


@cocotb.test
async def test_Combine_single(_) -> None:
    """Test Combine with a single trigger acts the same as awaiting the trigger directly."""
    combine = Combine(Timer(9, "ns"))
    with assert_takes(9, "ns"):
        res = await combine
    assert res is combine


@cocotb.test(timeout_time=10, timeout_unit="ns")
async def test_Combine_exception(dut) -> None:
    """Test Combine with exception ends immediately and isn't blocked by unfired triggers."""

    e = Event()  # we never plan on setting this

    async def raises_after_1ns():
        await Timer(1, "ns")
        raise MyException

    combine = Combine(cocotb.start_soon(raises_after_1ns()), Timer(10, "ns"), e.wait())
    with assert_takes(1, "ns"):
        with pytest.raises(MyException):
            await combine


@cocotb.test
async def test_First_empty(_) -> None:
    """Test that a First with no triggers raises an error."""
    with pytest.raises(ValueError):
        await First()


@cocotb.test
async def test_First_single(_) -> None:
    """Test First with a single trigger acts the same as awaiting the trigger directly."""
    timer = Timer(13, "ns")
    with assert_takes(13, "ns"):
        res = await First(timer)
    assert res is timer


@cocotb.test(timeout_time=10, timeout_unit="ns")
async def test_First_exception(_) -> None:
    """Test First with exception ends immediately and isn't blocked by unfired triggers."""

    e = Event()  # we never plan on setting this

    async def raises_after_1ns():
        await Timer(1, "ns")
        raise MyException

    first = First(cocotb.start_soon(raises_after_1ns()), Timer(10, "ns"), e.wait())
    with assert_takes(1, "ns"):
        with pytest.raises(MyException):
            await first


@cocotb.test
async def test_Combine_objects_shared_by_multiple(_: Any) -> None:
    """Test waiting for the same objects in multiple concurrent Combines."""
    count = 0
    events = [Event() for _ in range(5)]

    async def wait_for_all_events():
        nonlocal count
        await Combine(*(event.wait() for event in events))
        count += 1

    waiters = [cocotb.start_soon(wait_for_all_events()) for _ in range(5)]
    for e in events:
        e.set()
    await Combine(*waiters)
    assert count == 5


@cocotb.test
async def test_Lock_fair_scheduling(_) -> None:
    """Ensure that Lock acquisition is given in FIFO order to ensure fair access."""

    # test config
    n_waiters = 500
    waiter_ns = 1
    average_kills = 50
    average_test_time = (n_waiters - average_kills) * waiter_ns
    average_killer_wakeup = average_test_time / average_kills

    last_scheduled: int = -1
    lock = Lock()

    async def waiter(n: int) -> None:
        # Ensure the waiter didn't hang due another waiter being killed.
        with assert_takes(waiter_ns * (n + 1), "ns", lambda a, e: a <= e):
            await lock.acquire()

        # Ensure acquisition is in order.
        nonlocal last_scheduled
        assert n > last_scheduled
        last_scheduled = n

        # Hold the Lock for some time to give a chance for other waiters to be cancelled.
        await Timer(waiter_ns, "ns")
        lock.release()

    tasks: List[Task[None]] = []

    for i in range(n_waiters):
        tasks.append(cocotb.start_soon(waiter(i)))
        # Run the waiter until it gets the acquire()
        await NullTrigger()

    # We cancel tasks randomly to ensure that doesn't effect acquisition order.
    while not all(t.done() for t in tasks):
        # Randomly kill a remaining waiter.
        tasks[random.randrange(last_scheduled, len(tasks))].kill()
        # Wait some random time until killing another.
        await Timer(
            (random.random() * 2 * average_killer_wakeup), "ns", round_mode="ceil"
        )
        # So we don't depend upon the relative scheduling order of the waiter Timers and the above Timer.
        await ReadOnly()


@cocotb.test(expect_error=RuntimeError)
async def test_Lock_multiple_users_acquire_triggers(_) -> None:
    """Ensure that multiple Tasks using the same Lock.acquire() Triggers is not possible."""

    async def wait(trigger: Trigger) -> None:
        await trigger

    lock = Lock()
    acquire_trigger = lock.acquire()

    cocotb.start_soon(wait(acquire_trigger))
    cocotb.start_soon(wait(acquire_trigger))
    await Timer(1, "ns")


@cocotb.test(expect_error=RuntimeError)
async def test_Event_multiple_task_share_trigger(_) -> None:
    """Test that multiple tasks aren't allowed to share an Event trigger."""

    async def waiter(trigger: Trigger) -> None:
        await trigger

    e = Event()
    e_trigger = e.wait()
    cocotb.start_soon(waiter(e_trigger))
    cocotb.start_soon(waiter(e_trigger))

    await Timer(1, "ns")
