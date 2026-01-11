# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test HDL DUT ``sample_module``."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

import cocotb
from cocotb.triggers import FallingEdge
from cocotb_tools.pytest.hdl import HDL


@pytest.fixture(autouse=True)
async def sample_module_fixture(dut) -> AsyncGenerator[None, None]:
    """Setup/teardown sample module."""
    # Test setup (executed before test)
    dut.stream_in_valid.value = 0
    dut.stream_in_data.value = 0
    dut.stream_out_ready.value = 0

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
    await FallingEdge(dut.clk)


# cocotb marker is optional but it helps pytest-cocotb plugin to identify this function as cocotb runner and
# bind collected cocotb tests to cocotb runner during pytest tests collection:
# pytest --collect-only (in short: pytest --co)
# With that, user can use pytest -k '<expression>' to quickly filter tests that will be run by particular runner
@pytest.mark.cocotb_runner
def test_sample_module(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb_runner(
    "test_cocotb",
    "test_cocotb_top",
    "test_parametrize",
    "test_xfail",
    "test_caplog",
    "test_pass",
    "test_timeout",
)
def test_sample_module_extra(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb_runner("test_sample_module_1")
def test_sample_module_1(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb_runner("test_sample_module_1", "test_sample_module_2")
def test_sample_module_2(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb_runner("test_sample_module_1", "test_sample_module_2")
@pytest.mark.parametrize("int_param", (1, 4, 8))
def test_sample_module_parametrize(sample_module: HDL, int_param: int) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module["INT_PARAM"] = int_param
    sample_module.test()


def test_sample_module_without_marker(sample_module: HDL) -> None:
    """Test runner without using the :deco:`!pytest.mark.cocotb_runner` marker."""
    sample_module.test()


async def test_pass(dut) -> None:
    pass


async def test_simple(dut, start: int = 0, stop: int = 1, step: int = 1) -> None:
    """Test sample module with simple data transfer."""
    dut.stream_in_valid.value = 1
    dut.stream_out_ready.value = 1
    await FallingEdge(dut.clk)

    for data in range(start, stop, step):
        dut.stream_in_data.value = data
        await FallingEdge(dut.clk)

        assert dut.stream_out_data_registered.value == data


async def test_setup_only(dut) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut)


@pytest.mark.parametrize("start", [0, 4])
@pytest.mark.parametrize("stop", [6, 8, 10])
@pytest.mark.parametrize("step", [1, 2])
async def test_parametrize_matrix(dut, start: int, stop: int, step: int) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, start, stop, step)


@pytest.mark.parametrize("start,stop,step", [(0, 4, 1), (2, 8, 2)])
async def test_parametrize_series(dut, start: int, stop: int, step: int) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, start, stop, step)


@pytest.mark.parametrize("num", [1, 4, 8])
async def test_parametrize_single(dut, num: int) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, stop=num)


@pytest.mark.xfail(raises=RuntimeError, strict=True)
async def test_xfail_raises_string(dut) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut)
    raise RuntimeError("runtime error")


@pytest.mark.xfail(strict=True)
async def test_xfail_any(dut) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut)
    raise ValueError("value error")


@cocotb.xfail(raises=RuntimeError)
async def test_xfail_raises(dut) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut)
    raise RuntimeError("runtime error")
