# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Testing sample module."""

from __future__ import annotations

from typing import Callable

import pytest

from cocotb.clock import Clock
from cocotb.triggers import FallingEdge


# cocotb marker is optional but it helps pytest-cocotb plugin to identify this function as cocotb runner and
# bind collected cocotb tests to cocotb runner during pytest tests collection:
# pytest --collect-only (in short: pytest --co)
# With that, user can use pytest -k '<expression>' to quickly filter tests that will be run by particular runner
@pytest.mark.cocotb
def test_sample_module(cocotb_run: Callable[..., None]) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    cocotb_run()


@pytest.fixture(name="setup_teardown")
async def setup_teardown_fixture(dut):
    """Perform setup/teardown sequence for DUT."""
    # Test setup (executed before test)
    dut.clk.value = 0
    dut.stream_in_valid.value = 0
    dut.stream_in_data.value = 0
    dut.stream_out_ready.value = 0

    Clock(dut.clk, 10, unit="ns").start(start_high=False)

    for _ in range(2):
        await FallingEdge(dut.clk)

    yield  # Calling test

    # Test teardown (executed after test)
    dut.stream_in_valid.value = 0
    dut.stream_in_data.value = 0
    dut.stream_out_ready.value = 0

    # NOTE: Without it, Icarus simulator will crash with unexpected segmentation fault
    # at the end of the simulation. This also happen using built-in regression manager.
    # All other HDL simulators are fine, only Icarus is buggy
    # await FallingEdge(dut.clk)


async def test_sample_module_pass(dut) -> None:
    pass


async def test_sample_module_data_simple(dut, setup_teardown) -> None:
    """Test sample module with simple data transfer."""
    dut.stream_in_valid.value = 1
    dut.stream_out_ready.value = 1
    await FallingEdge(dut.clk)

    dut.stream_in_data.value = 10
    await FallingEdge(dut.clk)

    assert dut.stream_out_data_registered.value == 10


@pytest.mark.parametrize("num", [1, 4, 8])
async def test_sample_module_data_num(dut, setup_teardown, num: int) -> None:
    """Test sample module with simple data transfer."""
    dut.stream_in_valid.value = 1
    dut.stream_out_ready.value = 1
    await FallingEdge(dut.clk)

    for data in range(num):
        dut.stream_in_data.value = data
        await FallingEdge(dut.clk)

        assert dut.stream_out_data_registered.value == data


@pytest.mark.parametrize("start", [0, 4])
@pytest.mark.parametrize("stop", [6, 8, 10])
@pytest.mark.parametrize("step", [1, 2])
async def test_sample_module_data_range(
    dut, setup_teardown, start: int, stop: int, step: int
) -> None:
    """Test sample module with simple data transfer."""
    dut.stream_in_valid.value = 1
    dut.stream_out_ready.value = 1
    await FallingEdge(dut.clk)

    for data in range(start, stop, step):
        dut.stream_in_data.value = data
        await FallingEdge(dut.clk)

        assert dut.stream_out_data_registered.value == data


async def test_sample_module_data_reuse(dut, setup_teardown) -> None:
    """Test sample module with simple data transfer."""
    await test_sample_module_data_num(dut, setup_teardown, num=10)
