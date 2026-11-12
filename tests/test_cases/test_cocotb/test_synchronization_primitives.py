# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for synchronization primitives like Lock and Event
"""

from __future__ import annotations

import random
import re
from typing import Any

import pytest
from common import assert_takes

import cocotb
import cocotb.task
from cocotb._base_triggers import Trigger, _InternalEvent
from cocotb.task import Task
from cocotb.triggers import (
    Event,
    Lock,
    NullTrigger,
    ReadOnly,
    Timer,
    gather,
    select,
    with_timeout,
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
            for _ in range(4):
                await Timer(10, "ns")
                resource += 1

    cocotb.start_soon(co())
    async with lock:
        for _ in range(4):
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

    with pytest.warns(DeprecationWarning):
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
    e = _InternalEvent(lambda: "test parent")
    assert repr(e) == "test parent"

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

    tasks: list[Task[None]] = []

    for i in range(n_waiters):
        tasks.append(cocotb.start_soon(waiter(i)))
        # Run the waiter until it gets the acquire()
        await NullTrigger()

    # We cancel tasks randomly to ensure that doesn't effect acquisition order.
    while not all(t.done() for t in tasks):
        # Randomly kill a remaining waiter.
        tasks[random.randrange(last_scheduled, len(tasks))].cancel()
        # Wait some random time until killing another.
        await Timer(
            (random.random() * 2 * average_killer_wakeup), "ns", round_mode="ceil"
        )
        # So we don't depend upon the relative scheduling order of the waiter Timers and the above Timer.
        await ReadOnly()


@cocotb.test
async def test_Lock_retry_keeps_place_in_line(_) -> None:
    """Test that a Task which gives up acquiring a Lock and tries again keeps its place in line."""
    lock = Lock()
    give_up = Event()
    acquired: list[str] = []

    async def user(name: str) -> None:
        await lock.acquire()
        acquired.append(name)
        lock.release()

    async def retrier() -> None:
        # The first attempt is cancelled by select(), like a timeout would do.
        await select(lock.acquire(), give_up.wait())
        await user("retrier")

    await lock.acquire()
    retrier_task = cocotb.start_soon(retrier())
    await NullTrigger()
    give_up.set()
    await NullTrigger()
    # These Tasks start waiting after the retrier's first attempt.
    w1 = cocotb.start_soon(user("w1"))
    w2 = cocotb.start_soon(user("w2"))
    await NullTrigger()
    await NullTrigger()

    lock.release()
    await gather(retrier_task, w1, w2)

    assert acquired == ["retrier", "w1", "w2"]


@cocotb.test
async def test_Lock_given_up_attempt_is_skipped(_) -> None:
    """Test that a Lock is not held up by a Task which gave up acquiring it and never came back."""
    lock = Lock()
    acquired: list[str] = []

    async def user(name: str) -> None:
        await lock.acquire()
        acquired.append(name)
        lock.release()

    await lock.acquire()
    quitter = cocotb.start_soon(user("quitter"))
    await NullTrigger()
    w1 = cocotb.start_soon(user("w1"))
    w2 = cocotb.start_soon(user("w2"))
    await NullTrigger()
    assert re.search(r"\[3 waiting\]", repr(lock))

    # The quitter gives up while it is still waiting, then ends.
    quitter.cancel()
    await NullTrigger()
    assert quitter.cancelled()
    assert re.search(r"\[2 waiting\]", repr(lock))

    lock.release()
    await gather(w1, w2)

    assert acquired == ["w1", "w2"]
    assert not lock.locked()


@cocotb.test
async def test_Lock_await_given_up_trigger_again(_) -> None:
    """Test that a Lock.acquire() Trigger which was given up can be awaited again, and keeps its place in line."""
    lock = Lock()
    give_up = Event()
    acquired: list[str] = []

    async def user(name: str) -> None:
        await lock.acquire()
        acquired.append(name)
        lock.release()

    async def retrier() -> None:
        trigger = lock.acquire()
        await select(trigger, give_up.wait())
        # Wait on the same Trigger again, instead of calling acquire() again.
        await trigger
        acquired.append("retrier")
        lock.release()

    await lock.acquire()
    retrier_task = cocotb.start_soon(retrier())
    await NullTrigger()
    give_up.set()
    await NullTrigger()
    w1 = cocotb.start_soon(user("w1"))
    await NullTrigger()
    await NullTrigger()

    lock.release()
    await gather(retrier_task, w1)

    assert acquired == ["retrier", "w1"]
    assert not lock.locked()

    # The Lock is not left in a state where the retrier's Trigger is mistaken for a used one.
    await lock.acquire()
    lock.release()


@cocotb.test
async def test_Lock_forgets_given_up_attempts_of_finished_tasks(_) -> None:
    """Test that a Lock does not keep the attempts of Tasks that gave up and ended."""
    lock = Lock()

    async def quitter() -> None:
        # Gives up while waiting, as it is cancelled by select(), and then ends.
        await select(lock.acquire(), NullTrigger())

    await lock.acquire()
    # Each Task ends after giving up, so its place in line can never be used again.
    for _i in range(5):
        await cocotb.start_soon(quitter())
        await NullTrigger()

    # Nothing is waiting, and the places in line of the finished Tasks do not pile up.
    assert re.search(r"\[0 waiting\]", repr(lock))
    assert len(lock._pending_primed) <= 1

    lock.release()
    assert not lock.locked()
    # Everything given up has been dropped, the Lock still works.
    await lock.acquire()
    lock.release()


@cocotb.test
async def test_Lock_acquire_without_running_task(_) -> None:
    """Test that Lock.acquire() works when called outside of a Task."""
    lock = Lock()
    acquired: list[str] = []

    async def wait_for(trigger: Trigger, name: str) -> None:
        await trigger
        acquired.append(name)
        lock.release()

    await lock.acquire()

    # Simulate calling acquire() from outside a Task, for example from a callback.
    running_task = cocotb.task._current_task
    cocotb.task._current_task = None
    try:
        trigger = lock.acquire()
    finally:
        cocotb.task._current_task = running_task

    waiter = cocotb.start_soon(wait_for(trigger, "outside"))
    other = cocotb.start_soon(wait_for(lock.acquire(), "other"))
    await NullTrigger()
    assert re.search(r"\[2 waiting\]", repr(lock))

    # Nobody can come back for an attempt made outside of a Task, so it is dropped when its waiter is cancelled.
    waiter.cancel()
    await NullTrigger()
    assert re.search(r"\[1 waiting\]", repr(lock))

    lock.release()
    await other
    assert acquired == ["other"]
    assert not lock.locked()


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


@cocotb.test
async def test_Event_multiple_task_share_trigger(_) -> None:
    """Test that multiple tasks aren't allowed to share an Event trigger."""

    async def waiter(trigger: Trigger) -> None:
        await trigger

    e = Event()
    e_trigger = e.wait()
    cocotb.start_soon(waiter(e_trigger))
    cocotb.start_soon(waiter(e_trigger))

    await Timer(1, "ns")


class MyEvent(Event):
    pass


@cocotb.test
async def test_Event_repr(_: Any) -> None:
    """Test that an Event and its wait() Trigger repr their own type."""
    e = Event()
    assert re.match(r"<Event at \w+>", repr(e))

    e = MyEvent()
    assert re.match(r"<MyEvent at \w+>", repr(e))
    w = e.wait()
    assert re.match(r"<<MyEvent at \w+>\.wait\(\) at \w+>", repr(w))


@cocotb.test
async def test_Event_wait_after_set(_: Any) -> None:
    """Test that getting the _Event Trigger, setting it, then awaiting the Trigger doesn't hang."""

    e = Event()
    trigger = e.wait()

    e.set()

    # Should not block
    await with_timeout(trigger, 1, "step")
