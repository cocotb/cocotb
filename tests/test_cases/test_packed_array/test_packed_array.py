# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import pytest

import cocotb
from cocotb.handle import (
    ArrayObject,
    Immediate,
    LogicObject,
    PackedObject,
)
from cocotb.triggers import (
    ClockCycles,
    FallingEdge,
    RisingEdge,
    Timer,
    ValueChange,
)
from cocotb.types import Logic
from cocotb_tools.sim_versions import VerilatorVersion

xfail_without_packed_indexing = cocotb.xfail(
    cocotb.SIM_NAME.startswith("Verilator")
    and VerilatorVersion(cocotb.SIM_VERSION) < VerilatorVersion("5.048"),
    reason="Verilator does not index packed dimensions over VPI before v5.048",
)


@cocotb.test()
async def check_types(dut):
    """Check types"""

    assert type(dut.i_packed) is PackedObject
    assert type(dut.i_packed[0]) is PackedObject
    assert type(dut.i_packed[0][0]) is LogicObject
    assert type(dut.i_unpacked) is ArrayObject
    assert type(dut.i_mixed) is ArrayObject
    assert type(dut.i_short) is PackedObject
    assert type(dut.i_bit) is LogicObject
    assert type(dut.i_enum_arr2d) is PackedObject
    assert type(dut.i_union_arr2d) is PackedObject
    assert type(dut.i_pkt_arr2d) is PackedObject
    assert type(dut.i_enum_arr2d_unpk) is ArrayObject
    assert type(dut.i_union_arr2d_unpk) is ArrayObject
    assert type(dut.i_pkt_arr2d_unpk) is ArrayObject
    assert isinstance(dut.i_packed[0], PackedObject)
    assert isinstance(dut.i_packed[0][0], LogicObject)
    assert len(dut.i_packed) == 32


@cocotb.test()
async def flat_read_2d_element(dut):
    """Flat read 2-D element"""

    assert isinstance(dut.i_packed.value[1], Logic)


@cocotb.test()
async def read_write_2d_flat(dut):
    """Read/write flat 2-D packed array"""

    expected = 0xD
    dut.i_packed.value = expected
    await Timer(1)
    assert dut.o_packed.value == expected


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_2d_element(dut):
    """Read/write 2-D element"""

    expected = 0xD
    dut.i_packed[1].value = expected
    await Timer(1)
    assert dut.o_packed[1].value == expected


@cocotb.test()
async def read_write_2d_bit(dut):
    """Read/write 2-D bit"""

    expected = 1
    dut.i_packed[1][2].value = expected
    await Timer(1)
    assert dut.o_packed[1][2].value == expected


@cocotb.test()
async def read_write_3d_flat(dut):
    """Read/write flat 3-D packed array"""

    expected = 0xABCDEF
    dut.i_packed_3d.value = expected
    await Timer(1)
    assert dut.o_packed_3d.value == expected


@cocotb.test()
async def read_write_3d_outer_dimension(dut):
    """Read/write the outer 3-D packed dimension"""

    expected = 0xABC
    dut.i_packed_3d[1].value = expected
    await Timer(1)
    assert dut.o_packed_3d[1].value == expected


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_3d_middle_dimension(dut):
    """Read/write the middle 3-D packed dimension"""

    expected = 0xD
    dut.i_packed_3d[1][2].value = expected
    await Timer(1)
    assert dut.o_packed_3d[1][2].value == expected


@cocotb.test()
async def read_write_3d_bit(dut):
    """Read/write a 3-D packed bit"""

    dut.i_packed_3d[1][2][3].value = 1
    await Timer(1)
    assert dut.o_packed_3d[1][2][3].value == 1


@cocotb.test()
@xfail_without_packed_indexing
async def hierarchical_read_matches_flat_value(dut):
    """Read every 3-D packed element after writing a unique flat value"""

    dut.i_packed_3d.value = 0x012345
    await Timer(1)

    assert dut.o_packed_3d.value == 0x012345
    for expected, outer_index in zip(range(6), (1, 1, 1, 0, 0, 0)):
        middle_index = 2 - (expected % 3)
        element = dut.o_packed_3d[outer_index][middle_index]
        assert element.value == expected
        for bit_index in range(4):
            assert element[bit_index].value == (expected >> bit_index) & 1


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_mixed_ranges(dut):
    """Read/write a packed array with non-zero and mixed-direction ranges"""

    expected = {
        (5, 0): 0b000,
        (5, 1): 0b001,
        (5, 2): 0b010,
        (4, 0): 0b011,
        (4, 1): 0b100,
        (4, 2): 0b101,
    }
    dut.i_packed_mixed.value = 0b000_001_010_011_100_101
    await Timer(1)

    for index, value in expected.items():
        assert dut.o_packed_mixed[index[0]][index[1]].value == value
    assert dut.o_packed_mixed[4][2][-1].value == 1


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_indexed_width_boundaries(dut):
    """Read/write indexed packed dimensions at 1-, 32-, and 33-bit widths"""

    dut.i_packed_3d[1][2][3].value = 1
    dut.i_packed_32[0].value = 0x89ABCDEF
    dut.i_packed_wide[1][1][1].value = 0x1_0000_0001
    await Timer(1)

    assert dut.o_packed_3d[1][2][3].value == 1
    assert dut.o_packed_32[0].value == 0x89ABCDEF
    assert dut.o_packed_wide[1][1][1].value == 0x1_0000_0001
    assert dut.o_packed_wide[1][1][1][32].value == 1
    assert dut.o_packed_wide[1][1][1][0].value == 1


@cocotb.test()
async def immediate_write_to_indexed_dimension(dut):
    """Immediately write an indexed packed dimension"""

    expected = 0xE
    dut.i_packed_3d[1][0].value = Immediate(expected)
    assert dut.i_packed_3d[1][0].value == expected
    await Timer(1)
    assert dut.o_packed_3d[1][0].value == expected


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_typed_outer_dimensions(dut):
    """Read/write non-leaf dimensions of packed typed arrays"""

    dut.i_enum_arr2d[1].value = 0x6C
    dut.i_union_arr2d[1].value = 0x0123_4567_89AB_CDEF
    dut.i_pkt_arr2d[1].value = 0x123456789ABCDEF1234567
    await Timer(1)

    assert dut.o_enum_arr2d[1].value == 0x6C
    assert dut.o_union_arr2d[1].value == 0x0123_4567_89AB_CDEF
    assert dut.o_pkt_arr2d[1].value == 0x123456789ABCDEF1234567


@cocotb.test()
async def invalid_indexed_packed_dimensions(dut):
    """Reject invalid indexes at every packed dimension"""

    with pytest.raises(IndexError):
        dut.i_packed_3d[2]
    with pytest.raises(IndexError):
        dut.i_packed_3d[1][3]
    with pytest.raises(IndexError):
        dut.i_packed_3d[1][2][4]
    with pytest.raises(IndexError):
        dut.i_packed_3d[-1]
    with pytest.raises(TypeError):
        dut.i_packed_3d[1:0]


@cocotb.test()
@xfail_without_packed_indexing
async def iterate_2d(dut):
    """Iterate 2d"""

    values = [0xA, 0xB, 0xC, 0xD]
    for handle, val in zip(dut.i_packed, values):
        handle.value = val
        await Timer(1)

    for handle, val in zip(dut.o_packed, values):
        assert handle.value == val


# Multidimensional arrays with typed elements


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_enum_2d_element(dut):
    """Read/write enum"""

    assert len(dut.i_enum_arr2d) == 16
    expected = 3  # WHITE
    dut.i_enum_arr2d[1][2].value = expected
    await Timer(1)
    assert dut.o_enum_arr2d[1][2].value == expected


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_union_2d_element(dut):
    """Read/write union"""

    assert len(dut.o_union_arr2d) == 128
    expected = 0xABCD
    dut.i_union_arr2d[1][2].value = expected
    await Timer(1)
    assert dut.o_union_arr2d[1][2].value == expected


@cocotb.test()
@xfail_without_packed_indexing
async def read_write_struct_2d_element(dut):
    """Read/write struct"""

    assert len(dut.o_pkt_arr2d) == 176
    expected = 0x2AAAAA
    dut.i_pkt_arr2d[1][2].value = expected
    await Timer(1)
    assert dut.o_pkt_arr2d[1][2].value == expected


# Events/triggers on an indexed element


async def _drive_edges(signal, values):
    for value in values:
        signal.value = value
        await Timer(1)


@cocotb.test()
async def edge_clk(dut):
    """Drive and wait for an edge on a clock"""
    sig = dut.clk
    cocotb.start_soon(_drive_edges(sig, [1, 0]))
    await FallingEdge(sig)
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    await RisingEdge(sig)


@cocotb.test()
async def edge_2d_bit(dut):
    """Drive and wait for an edge on one bit of a 2-D packed array"""
    sig = dut.i_packed[0][0]
    cocotb.start_soon(_drive_edges(sig, [1, 0]))
    await FallingEdge(sig)
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    await RisingEdge(sig)


@cocotb.test()
async def any_edge_2d_bit(dut):
    """Drive and wait for any edge on one bit of a 2-D packed array"""

    sig = dut.i_packed[0][1]
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    assert (await sig.value_change) is sig.value_change


@cocotb.test()
async def rising_edge_3d_bit(dut):
    """Drive and wait for a rising edge on one bit of a 3-D packed array"""

    sig = dut.i_packed_3d[0][0][0]
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    await RisingEdge(sig)


@cocotb.test()
async def value_change_2d_element(dut):
    """Drive and wait for a whole 2-D element to change"""

    sig = dut.i_packed[1]
    cocotb.start_soon(_drive_edges(sig, [0x5, 0xA]))
    await ValueChange(sig)


@cocotb.test()
async def value_change_3d(dut):
    """Drive and wait for a rising edge on a 3-D packed array"""

    sig = dut.i_packed_3d
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    await ValueChange(sig)


@cocotb.test()
async def value_change_3d_outer_dimension(dut):
    """Drive and wait for a rising edge on outer dimension of a 3-D packed array"""

    sig = dut.i_packed_3d[0]
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    await ValueChange(sig)


@cocotb.test()
async def value_change_3d_middle_dimension(dut):
    """Drive and wait for a rising edge on middle dimension of a 3-D packed array"""

    sig = dut.i_packed_3d[0][0]
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    await ValueChange(sig)


@cocotb.test()
async def value_change_enum_element(dut):
    """Drive and wait for an enum-array element to change"""

    sig = dut.i_enum_arr2d[0][0]
    cocotb.start_soon(_drive_edges(sig, [0, 1]))
    await ValueChange(sig)


@cocotb.test()
async def value_change_union_element(dut):
    """Drive and wait for a union-array element to change"""

    sig = dut.i_union_arr2d[0][0]
    cocotb.start_soon(_drive_edges(sig, [0x0000, 0xABCD]))
    await ValueChange(sig)


@cocotb.test()
async def value_change_struct_element(dut):
    """Drive and wait for a struct-array element to change"""

    sig = dut.i_pkt_arr2d[0][0]
    cocotb.start_soon(_drive_edges(sig, [0x000000, 0x2AAAAA]))
    await ValueChange(sig)


@cocotb.test()
async def clock_cycles_on_2d_bit(dut):
    """Drive one bit of a 2-D packed array as a clock and count 3 edges"""

    sig = dut.i_packed[0][0]
    cocotb.start_soon(_drive_edges(sig, [0, 1, 0, 1, 0, 1, 0, 1]))
    await ClockCycles(sig, 3)


@cocotb.test()
async def edge_storm_3d(dut):
    """Sensitivity: await rising/falling edges on a single bit in 3-D packed array"""

    async def _toggle(signal, iterations: int):
        value = 0
        for _ in range(iterations):
            value ^= 1
            signal.value = value
            await Timer(1)

    ITERATIONS = 1
    sig_i = dut.i_packed_3d[0][0][0]
    cocotb.start_soon(_toggle(sig_i, ITERATIONS * 2))
    sig_o = dut.o_packed_3d[0][0][0]
    for _ in range(ITERATIONS):
        await RisingEdge(sig_o)
        await FallingEdge(sig_o)
