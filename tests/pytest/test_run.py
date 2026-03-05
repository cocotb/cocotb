# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

import cocotb
from cocotb.triggers import Event


def test_run() -> None:
    a = 1

    async def coro() -> int:
        nonlocal a
        a = 2
        return 42

    result = cocotb.run(coro())
    assert result == 42
    assert a == 2


def test_run_exception() -> None:
    a = 1

    async def coro() -> None:
        nonlocal a
        a = 2
        raise ValueError("test")

    with pytest.raises(ValueError, match="test"):
        cocotb.run(coro())
    assert a == 2


def test_run_with_start_soon() -> None:
    a = 1

    async def coro() -> None:
        e = Event()

        async def other_task() -> None:
            nonlocal a
            a = 2
            e.set()

        cocotb.start_soon(other_task())
        await e.wait()

    cocotb.run(coro())
    assert a == 2
