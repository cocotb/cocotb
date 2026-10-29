# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, Timer, ValueChange

ITERATIONS = 1000


@cocotb.test()
async def write_flat_2d(dut):
    """Repeatedly write 2-D packed array in one shot."""
    for i in range(ITERATIONS):
        dut.i_wide_2d.value = i
    await Timer(1)


@cocotb.test()
async def read_flat_2d(dut):
    """Repeatedly read 2-D packed array."""
    n = dut.i_wide_2d.size
    dut.i_wide_2d.value = (1 << n) - 1
    await Timer(1)
    for _ in range(ITERATIONS):
        _ = dut.o_wide_2d.value


@cocotb.test()
async def write_indexed_2d(dut):
    """Write individual outer-dimension elements of 2-D packed array."""
    n = dut.i_wide_2d.range.left + 1
    for i in range(ITERATIONS):
        dut.i_wide_2d[i % n].value = i
    await Timer(1)


@cocotb.test()
async def write_read_indexed_3d(dut):
    """Write and read back nested indices of 3-D packed array."""
    n_outer = dut.i_wide_3d.range.left + 1
    n_middle = dut.i_wide_3d[0].range.left + 1
    for i in range(ITERATIONS):
        outer = i % n_outer
        middle = i % n_middle
        dut.i_wide_3d[outer][middle].value = i
        await Timer(1)
        assert dut.o_wide_3d[outer][middle].value == i


async def _toggle(signal, iterations: int):
    value = 0
    for _ in range(iterations):
        value ^= 1
        signal.value = value
        await Timer(1)


@cocotb.test()
async def value_change_element_2d(dut):
    """Sensitivity: await value-change events on one element inside 2-D packed array."""
    sig = dut.o_wide_2d[0][0]
    cocotb.start_soon(_toggle(sig, ITERATIONS))
    for _ in range(ITERATIONS):
        await ValueChange(sig)


@cocotb.test()
async def value_change_3d(dut):
    """Sensitivity: await value-change events on 3-D packed array."""
    ITERATIONS = 100
    sig_i = dut.i_wide_3d
    cocotb.start_soon(_toggle(sig_i, ITERATIONS))
    sig_o = dut.o_wide_3d
    for _ in range(ITERATIONS):
        await ValueChange(sig_o)


@cocotb.test()
async def value_change_bit_3d(dut):
    """Sensitivity: await value-change events on a bit from 3-D packed array."""
    sig_i = dut.i_wide_3d[0][0][0]
    cocotb.start_soon(_toggle(sig_i, ITERATIONS))
    sig_o = dut.o_wide_3d[0][0][0]
    for _ in range(ITERATIONS):
        await ValueChange(sig_o)


@cocotb.test()
async def value_change_middle_3d(dut):
    """Sensitivity: await value-change events on middle index of 3-D packed array."""
    sig_i = dut.i_wide_3d[0][0]
    cocotb.start_soon(_toggle(sig_i, ITERATIONS))
    sig_o = dut.o_wide_3d[0][0]
    for _ in range(ITERATIONS):
        await ValueChange(sig_o)


@cocotb.test()
async def edge_storm_2d(dut):
    """Sensitivity: await rising/falling edges on a single bit in 2-D packed array."""
    sig = dut.i_wide_2d[0][0]
    cocotb.start_soon(_toggle(sig, ITERATIONS * 2))
    for _ in range(ITERATIONS):
        await RisingEdge(sig)
        await FallingEdge(sig)


@cocotb.test()
async def edge_storm_3d(dut):
    """Sensitivity: await rising/falling edges on a single bit in 3-D packed array."""
    sig_i = dut.i_wide_3d[0][0][0]
    cocotb.start_soon(_toggle(sig_i, ITERATIONS * 2))
    sig_o = dut.o_wide_3d[0][0][0]
    for _ in range(ITERATIONS):
        await RisingEdge(sig_o)
        await FallingEdge(sig_o)
