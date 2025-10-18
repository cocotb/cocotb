# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Test function and substitutability of async coroutines
"""

from __future__ import annotations

import pytest
from common import MyException

import cocotb
from cocotb._outcomes import Error, Value
from cocotb.task import Task
from cocotb.triggers import Timer


class produce:
    """Test helpers that produce a value / exception in different ways"""

    @staticmethod
    async def async_(outcome):
        await Timer(1)
        return outcome.get()


@cocotb.test()
async def test_async_from_async(dut):
    """Test that async coroutines are able to call raw async functions"""
    v = await produce.async_(Value(1))
    assert v == 1

    try:
        await produce.async_(Error(MyException))
    except MyException:
        pass
    else:
        assert False


@cocotb.test()
async def test_trigger_await_gives_self(dut):
    """Test that await returns the trigger itself for triggers"""
    t = Timer(1)
    t2 = await t
    assert t2 is t


@cocotb.test()
async def test_fork_coroutine_function_exception(dut):
    async def coro():
        pass

    pattern = f"Coroutine function {coro} should be called prior to being scheduled."
    with pytest.raises(TypeError, match=pattern):
        cocotb.start_soon(coro)


@cocotb.test()
async def test_task_coroutine_function_exception(dut):
    async def coro(dut):
        pass

    pattern = f"Coroutine function {coro} should be called prior to being scheduled."
    with pytest.raises(TypeError, match=pattern):
        Task(coro)
