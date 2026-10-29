# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests for the First and Combine scaffolding.

First and Combine are implemented in terms of select and gather,
whose behavior is tested in test_waiters.py.
The tests here cover only what First and Combine add on top:
argument checking, the deprecated Task arguments, what awaiting them returns,
and nesting.
"""

from __future__ import annotations

import pytest
from common import MyException, assert_takes

import cocotb
from cocotb.triggers import Combine, Event, First, Timer


@cocotb.test
async def test_Combine_empty(_: object) -> None:
    """Test that a Combine with no triggers passes no time."""
    combine = Combine()
    with assert_takes(0, "ns"):
        res = await combine
    assert res is combine


@cocotb.test
async def test_Combine_single(_: object) -> None:
    """Test Combine with a single trigger acts the same as awaiting the trigger directly."""
    combine = Combine(Timer(9, "ns"))
    with assert_takes(9, "ns"):
        res = await combine
    assert res is combine


@cocotb.test
async def test_Combine_repr(_: object) -> None:
    """Test that Combine reprs its child triggers."""
    timer = Timer(1, "ns")
    assert repr(Combine(timer)) == f"Combine({timer!r})"


@cocotb.test
async def test_nested_combine(_: object) -> None:
    """Test passing a Combine trigger directly to another Combine trigger."""
    combine = Combine(Combine(Timer(10, "ns"), Timer(20, "ns")), Timer(30, "ns"))
    with assert_takes(30, "ns"):
        res = await combine
    assert res is combine


@cocotb.test(timeout_time=10, timeout_unit="ns")
async def test_Combine_exception(_: object) -> None:
    """Test Combine with exception ends immediately and isn't blocked by unfired triggers."""

    e = Event()  # we never plan on setting this

    async def raises_after_1ns() -> None:
        await Timer(1, "ns")
        raise MyException

    with pytest.warns(DeprecationWarning):
        combine = Combine(
            cocotb.start_soon(raises_after_1ns()), Timer(10, "ns"), e.wait()
        )
    with assert_takes(1, "ns"), pytest.raises(MyException):
        await combine


@cocotb.test
async def test_Combine_task_deprecated(_: object) -> None:
    """Test that passing Tasks to Combine is deprecated, but still waits for them all."""

    async def coro(delay: int) -> None:
        await Timer(delay, "ns")

    tasks = [cocotb.start_soon(coro(delay)) for delay in (10, 30, 20)]

    with pytest.warns(DeprecationWarning):
        combine = Combine(*tasks)
    with assert_takes(30, "ns"):
        await combine


@cocotb.test
async def test_First_empty(_: object) -> None:
    """Test that a First with no triggers raises an error."""
    with pytest.raises(ValueError):
        await First()


@cocotb.test
async def test_First_single(_: object) -> None:
    """Test First with a single trigger acts the same as awaiting the trigger directly."""
    timer = Timer(13, "ns")
    with assert_takes(13, "ns"):
        res = await First(timer)
    assert res is timer


@cocotb.test
async def test_nested_first(_: object) -> None:
    """Test that a nested First unpacks completely, rather than just by one level."""
    timer = Timer(1, "ns")
    inner_first = First(timer, Timer(2, "ns"))
    with assert_takes(1, "ns"):
        res = await First(inner_first, Timer(3, "ns"))
    assert res is not inner_first
    assert res is timer


@cocotb.test
async def test_First_task_deprecated(_: object) -> None:
    """Test that passing Tasks to First is deprecated, but still returns the first result."""

    async def coro() -> None:
        await Timer(2, "ns")

    task = cocotb.start_soon(coro())
    timer = Timer(1, "ns")

    with pytest.warns(DeprecationWarning):
        first = First(timer, task)
    with assert_takes(1, "ns"):
        res = await first
    assert res is timer

    # the Task that did not finish first is not killed
    assert not task.done()
    await task


@cocotb.test
async def test_invalid_trigger_types(_: object) -> None:
    """Test that First and Combine type-check their arguments up front."""
    o = object()

    with pytest.raises(TypeError):
        await First(Timer(1, "ns"), o)

    with pytest.raises(TypeError):
        await Combine(Timer(1, "ns"), o)


@cocotb.test(timeout_time=5, timeout_unit="ns")
async def test_5594(_: object) -> None:

    async def other_coro(e1: Event, e2: Event) -> None:
        # wait for e1 to be set by the test
        await e1.wait()

        # set e2 to let the test know we passed the wait
        e2.set()
        e2.clear()

    e1 = Event()
    e2 = Event()
    cocotb.start_soon(other_coro(e1, e2))

    # Ensure other_coro is waiting on e1 before we set it
    await Timer(1, "ns")

    # Wake up other_coro
    e1.set()
    e1.clear()

    # Wait for other_coro to set e2
    await First(e2.wait())
