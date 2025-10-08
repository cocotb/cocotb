# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for concurrency primitives like First and Combine
"""

from __future__ import annotations

import contextlib
import re
from collections import deque
from random import randint
from typing import Any

import pytest
from common import MyException, _check_traceback, assert_takes

import cocotb
from cocotb.task import Task
from cocotb.triggers import Combine, Event, First, Timer, Trigger


class MyTrigger(Trigger):
    def __init__(self) -> None:
        super().__init__()
        self.primed = 0
        self.unprimed = 0

    def _prime(self) -> None:
        self.primed += 1

    def _unprime(self) -> None:
        self.unprimed += 1


@cocotb.test
async def test_First_unfired_triggers_killed(_) -> None:
    """Test that un-fired trigger(s) in First don't later cause a spurious wakeup."""

    triggers = [MyTrigger() for _ in range(3)]

    timer = Timer(1, "ns")
    res = await First(timer, *triggers)
    assert res is timer

    for t in triggers:
        assert t.primed == 1
        assert t.unprimed == 1


@cocotb.test
async def test_First_unfired_triggers_killed_on_exception(_) -> None:
    """Test that un-fired trigger(s) in First after exception don't later cause a spurious wakeup."""

    triggers = [MyTrigger() for _ in range(3)]

    async def fails() -> None:
        raise ValueError("I am a failure")

    with contextlib.suppress(ValueError):
        await First(cocotb.start_soon(Task(fails())), *triggers)

    for t in triggers:
        assert t.primed == 1
        assert t.unprimed == 1


@cocotb.test
async def test_Combine_unfired_triggers_killed_on_exception(_) -> None:
    """Test that un-fired trigger(s) in Combine after exception don't later cause a spurious wakeup."""

    triggers = [MyTrigger() for _ in range(3)]

    async def fails() -> None:
        raise ValueError("I am a failure")

    with contextlib.suppress(ValueError):
        await Combine(cocotb.start_soon(Task(fails())), *triggers)

    for t in triggers:
        assert t.primed == 1
        assert t.unprimed == 1


@cocotb.test()
async def test_nested_first(dut):
    """Test that nested First triggers behave as expected"""
    events = [Event() for i in range(3)]
    waiters = [e.wait() for e in events]

    async def fire_events():
        """fire the events in order"""
        for e in events:
            await Timer(1, "ns")
            e.set()

    async def wait_for_nested_first():
        inner_first = First(waiters[0], waiters[1])
        ret = await First(inner_first, waiters[2])

        # should unpack completely, rather than just by one level
        assert ret is not inner_first
        assert ret is waiters[0]

    fire_task = cocotb.start_soon(fire_events())
    await wait_for_nested_first()
    await fire_task


@cocotb.test()
async def test_first_does_not_kill(dut):
    """Test that `First` does not kill coroutines that did not finish first"""
    ran = False

    async def coro():
        nonlocal ran
        await Timer(2, unit="ns")
        ran = True

    # Coroutine runs for 2ns, so we expect the timer to fire first
    timer = Timer(1, unit="ns")
    t = await First(timer, cocotb.start_soon(coro()))
    assert t is timer
    assert not ran

    # the background routine is still running, but should finish after 1ns
    await Timer(2, unit="ns")

    assert ran


@cocotb.test()
async def test_exceptions_first(dut):
    """Test exception propagation via cocotb.triggers.First"""

    async def raise_inner():
        await Timer(10, "ns")
        raise ValueError("It is soon now")

    async def raise_soon():
        await Timer(1, "ns")
        await cocotb.triggers.First(cocotb.start_soon(raise_inner()))

    await _check_traceback(
        raise_soon(), ValueError, r".*in raise_soon.*in raise_inner", re.DOTALL
    )


@cocotb.test()
async def test_combine(dut):
    """Test the Combine trigger."""
    # gh-852

    async def coro(delay):
        await Timer(delay, "ns")

    tasks = [cocotb.start_soon(coro(dly)) for dly in [10, 30, 20]]

    await Combine(*tasks)


@cocotb.test()
async def test_fork_combine(dut):
    """Test the Combine trigger with forked coroutines."""
    # gh-852

    async def coro(delay):
        await Timer(delay, "ns")

    tasks = [cocotb.start_soon(coro(dly)) for dly in [10, 30, 20]]

    await Combine(*tasks)


@cocotb.test()
async def test_event_is_set(dut):
    e = Event()

    assert not e.is_set()
    e.set()
    assert e.is_set()
    e.clear()
    assert not e.is_set()


@cocotb.test()
async def test_combine_start_soon(_):
    async def coro(delay):
        await Timer(delay, "ns")

    max_delay = 10

    tasks = [cocotb.start_soon(coro(d)) for d in range(1, max_delay + 1)]

    with assert_takes(max_delay, "ns"):
        await Combine(*tasks)


@cocotb.test()
async def test_recursive_combine_and_start_soon(_):
    """Test using `Combine` on forked coroutines that themselves use `Combine`."""

    async def mergesort(n):
        if len(n) == 1:
            return n
        part1 = n[: len(n) // 2]
        part2 = n[len(n) // 2 :]
        sort1 = cocotb.start_soon(mergesort(part1))
        sort2 = cocotb.start_soon(mergesort(part2))
        await Combine(sort1, sort2)
        res1 = deque(sort1.result())
        res2 = deque(sort2.result())
        res = []
        while res1 and res2:
            if res1[0] < res2[0]:
                res.append(res1.popleft())
            else:
                res.append(res2.popleft())
        res.extend(res1)
        res.extend(res2)
        return res

    t = [randint(0, 1000) for _ in range(100)]
    res = await mergesort(t)
    t.sort()
    assert t == res


@cocotb.test()
async def test_recursive_combine(_):
    """Test passing a `Combine` trigger directly to another `Combine` trigger."""

    done = set()

    async def waiter(N):
        await Timer(N, "ns")
        done.add(N)

    with assert_takes(30, "ns"):
        await Combine(
            Combine(cocotb.start_soon(waiter(10)), cocotb.start_soon(waiter(20))),
            cocotb.start_soon(waiter(30)),
        )
    assert done == {10, 20, 30}


class MyEvent(Event):
    pass


@cocotb.test
async def test_concurrency_trigger_repr(_):
    e = Event()
    assert re.match(r"<Event at \w+>", repr(e))

    e = MyEvent()
    assert re.match(r"<MyEvent at \w+>", repr(e))
    w = e.wait()
    assert re.match(r"<<MyEvent at \w+>\.wait\(\) at \w+>", repr(w))


@cocotb.test()
async def test_invalid_trigger_types(dut):
    o = object()

    with pytest.raises(TypeError):
        await First(Timer(1), o)

    with pytest.raises(TypeError):
        await Combine(Timer(1), o)


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
    with assert_takes(1, "ns"), pytest.raises(MyException):
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
    with assert_takes(1, "ns"), pytest.raises(MyException):
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
async def test_Combine_task_cancelled(_: Any) -> None:
    """Test that cancelling a Task waiting on a Combine cleans waiter tasks."""

    triggers = [MyTrigger() for _ in range(5)]

    async def waiter() -> None:
        await Combine(*triggers)

    task = cocotb.start_soon(waiter())
    await Timer(1, "ns")
    for t in triggers:
        assert t.primed == 1
    for t in triggers:
        assert t.unprimed == 0
    task.cancel()
    await Timer(1, "ns")
    for t in triggers:
        assert t.primed == 1
    for t in triggers:
        assert t.unprimed == 1


@cocotb.test
async def test_First_task_cancelled(_: Any) -> None:
    """Test that cancelling a Task waiting on a First cleans waiter tasks."""

    triggers = [MyTrigger() for _ in range(5)]

    async def waiter() -> None:
        await First(*triggers)

    task = cocotb.start_soon(waiter())
    await Timer(1, "ns")
    for t in triggers:
        assert t.primed == 1
    for t in triggers:
        assert t.unprimed == 0
    task.cancel()
    await Timer(1, "ns")
    for t in triggers:
        assert t.primed == 1
    for t in triggers:
        assert t.unprimed == 1


@cocotb.test
async def test_Combine_task_being_waited_cancelled(_: Any) -> None:
    """Test cancelling a Task being awaited by a Combine causes it to finish."""
    e = Event()

    async def wait_forever() -> None:
        await e.wait()

    tasks = [cocotb.start_soon(wait_forever()) for _ in range(5)]

    async def wait_on_tasks() -> None:
        await Combine(*tasks)

    waiter_task = cocotb.start_soon(wait_on_tasks())
    await Timer(1, "ns")

    # cancel just one task
    tasks[0].cancel()

    # check other tasks haven't been cancelled and the Combine isn't finished.
    await Timer(1, "ns")
    assert not waiter_task.done()
    for t in tasks[1:]:
        assert not t.done()

    # cancel remaining tasks
    for t in tasks[1:]:
        t.cancel()

    # see if that finishes the Combine
    await Timer(1, "ns")
    assert waiter_task.done()


@cocotb.test
async def test_First_task_being_waited_cancelled(_: Any) -> None:
    """Test cancelling a Task being awaited by a First causes it to finish."""
    e = Event()

    async def wait_forever() -> None:
        await e.wait()

    tasks = [cocotb.start_soon(wait_forever()) for _ in range(5)]

    async def wait_on_tasks() -> None:
        await First(*tasks)

    waiter_task = cocotb.start_soon(wait_on_tasks())
    await Timer(1, "ns")

    # cancel just one task
    tasks[0].cancel()

    # check other tasks have been cancelled and the Combine is finished.
    await Timer(1, "ns")
    assert waiter_task.done()
    for t in tasks[1:]:
        assert not t.done()
