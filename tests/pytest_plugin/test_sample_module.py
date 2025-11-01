# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test HDL DUT ``sample_module``."""

from __future__ import annotations

import pytest

import cocotb
from cocotb.triggers import FallingEdge
from cocotb_tools.pytest.hdl import HDL


# cocotb marker is optional but it helps pytest-cocotb plugin to identify this function as cocotb runner and
# bind collected cocotb tests to cocotb runner during pytest tests collection:
# pytest --collect-only (in short: pytest --co)
# With that, user can use pytest -k '<expression>' to quickly filter tests that will be run by particular runner
@pytest.mark.cocotb
def test_sample_module(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb(
    "test_cocotb",
    "test_parametrize",
    "test_xfail",
)
def test_sample_module_extra(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb("test_sample_module_1")
def test_sample_module_1(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb("test_sample_module_1", "test_sample_module_2")
def test_sample_module_2(sample_module: HDL) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module.test()


@pytest.mark.cocotb("test_sample_module_1", "test_sample_module_2")
@pytest.mark.parametrize("int_param", (1, 4, 8))
def test_sample_module_parametrize(sample_module: HDL, int_param: int) -> None:
    """Running HDL simulator using cocotb runner for sample module."""
    sample_module["INT_PARAM"] = int_param
    sample_module.test()


async def test_pass(dut) -> None:
    pass


async def test_simple(
    dut, sample_module_setup, start: int = 0, stop: int = 1, step: int = 1
) -> None:
    """Test sample module with simple data transfer."""
    dut.stream_in_valid.value = 1
    dut.stream_out_ready.value = 1
    await FallingEdge(dut.clk)

    for data in range(start, stop, step):
        dut.stream_in_data.value = data
        await FallingEdge(dut.clk)

        assert dut.stream_out_data_registered.value == data


async def test_setup_only(dut, clock_generation) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, clock_generation)


@pytest.mark.parametrize("start", [0, 4])
@pytest.mark.parametrize("stop", [6, 8, 10])
@pytest.mark.parametrize("step", [1, 2])
async def test_parametrize_matrix(
    dut, sample_module_setup, start: int, stop: int, step: int
) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, sample_module_setup, start, stop, step)


@pytest.mark.parametrize("start,stop,step", [(0, 4, 1), (2, 8, 2)])
async def test_parametrize_series(
    dut, sample_module_setup, start: int, stop: int, step: int
) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, sample_module_setup, start, stop, step)


@pytest.mark.parametrize("num", [1, 4, 8])
async def test_parametrize_single(dut, sample_module_setup, num: int) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, sample_module_setup, stop=num)


@pytest.mark.xfail(raises=RuntimeError, strict=True)
async def test_xfail_raises_string(dut, sample_module_setup) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, sample_module_setup)
    raise RuntimeError("runtime error")


@pytest.mark.xfail(strict=True)
async def test_xfail_any(dut, sample_module_setup) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, sample_module_setup)
    raise ValueError("value error")


@cocotb.xfail(raises=RuntimeError)
async def test_xfail_raises(dut, sample_module_setup) -> None:
    """Test sample module with simple data transfer."""
    await test_simple(dut, sample_module_setup)
    raise RuntimeError("runtime error")
