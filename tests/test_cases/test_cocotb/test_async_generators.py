# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

import cocotb
from cocotb.task import Task


async def whoops_async_generator():
    # the user should have used `await` here, but they wrote `yield` by accident.
    yield cocotb.triggers.Timer(1)


@cocotb.test
async def test_forking_accidental_async_generator(_) -> None:
    with pytest.raises(TypeError) as e:
        cocotb.start_soon(whoops_async_generator())

    assert "async generator" in str(e)


@cocotb.test
async def test_constructing_accidental_async_generator(_) -> None:
    with pytest.raises(TypeError) as e:
        Task(whoops_async_generator())

    assert "async generator" in str(e)


@cocotb.test
async def test_creating_accidental_async_generator(_) -> None:
    with pytest.raises(TypeError) as e:
        cocotb.create_task(whoops_async_generator())

    assert "async generator" in str(e)


@cocotb.test
async def test_awaiting_accidental_async_generator(_) -> None:
    with pytest.raises(TypeError):
        await whoops_async_generator()

    # Python handles this so we don't want to presume what the error message is
