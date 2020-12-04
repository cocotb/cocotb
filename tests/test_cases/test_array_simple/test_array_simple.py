# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Test getting and setting values of arrays"""
import contextlib
import logging

import cocotb
from cocotb.clock import Clock
from cocotb.result import TestFailure
from cocotb.triggers import Timer

tlog = logging.getLogger("cocotb.test")


def _check_value(tlog, hdl, expected):
    if hdl.value != expected:
        raise TestFailure("{2!r}: Expected >{0}< but got >{1}<".format(expected, hdl.value, hdl))
    else:
        tlog.info("   Found {0!r} ({1}) with value={2}".format(hdl, hdl._type, hdl.value))


@cocotb.test()
async def test_1dim_array_handles(dut):
    """Test getting and setting array values using the handle of the full array."""

    cocotb.fork(Clock(dut.clk, 1000, 'ns').start())

    # Set values with '<=' operator
    dut.array_7_downto_4 <= [0xF0, 0xE0, 0xD0, 0xC0]
    dut.array_4_to_7     <= [0xB0, 0xA0, 0x90, 0x80]
    dut.array_3_downto_0 <= [0x70, 0x60, 0x50, 0x40]
    dut.array_0_to_3     <= [0x30, 0x20, 0x10, 0x00]

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_7_downto_4, [0xF0, 0xE0, 0xD0, 0xC0])
    _check_value(tlog, dut.array_4_to_7    , [0xB0, 0xA0, 0x90, 0x80])
    _check_value(tlog, dut.array_3_downto_0, [0x70, 0x60, 0x50, 0x40])
    _check_value(tlog, dut.array_0_to_3    , [0x30, 0x20, 0x10, 0x00])

    # Set values through HierarchyObject.__setattr__ method on 'dut' handle
    dut.array_7_downto_4 = [0x00, 0x11, 0x22, 0x33]
    dut.array_4_to_7     = [0x44, 0x55, 0x66, 0x77]
    dut.array_3_downto_0 = [0x88, 0x99, 0xAA, 0xBB]
    dut.array_0_to_3     = [0xCC, 0xDD, 0xEE, 0xFF]

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_7_downto_4, [0x00, 0x11, 0x22, 0x33])
    _check_value(tlog, dut.array_4_to_7    , [0x44, 0x55, 0x66, 0x77])
    _check_value(tlog, dut.array_3_downto_0, [0x88, 0x99, 0xAA, 0xBB])
    _check_value(tlog, dut.array_0_to_3    , [0xCC, 0xDD, 0xEE, 0xFF])


@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl")))
async def test_ndim_array_handles(dut):
    """Test getting and setting multi-dimensional array values using the handle of the full array."""

    cocotb.fork(Clock(dut.clk, 1000, 'ns').start())

    # Set values with '<=' operator
    dut.array_2d <= [
        [0xF0, 0xE0, 0xD0, 0xC0],
        [0xB0, 0xA0, 0x90, 0x80]
    ]

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_2d, [[0xF0, 0xE0, 0xD0, 0xC0], [0xB0, 0xA0, 0x90, 0x80]])

    # Set values through HierarchyObject.__setattr__ method on 'dut' handle
    dut.array_2d = [
        [0x00, 0x11, 0x22, 0x33],
        [0x44, 0x55, 0x66, 0x77]
    ]

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_2d, [[0x00, 0x11, 0x22, 0x33], [0x44, 0x55, 0x66, 0x77]])


@cocotb.test()
async def test_1dim_array_indexes(dut):
    """Test getting and setting values of array indexes."""

    cocotb.fork(Clock(dut.clk, 1000, 'ns').start())

    dut.array_7_downto_4 <= [0xF0, 0xE0, 0xD0, 0xC0]
    dut.array_4_to_7     <= [0xB0, 0xA0, 0x90, 0x80]
    dut.array_3_downto_0 <= [0x70, 0x60, 0x50, 0x40]
    dut.array_0_to_3     <= [0x30, 0x20, 0x10, 0x00]

    await Timer(1000, 'ns')

    # Check indices
    _check_value(tlog, dut.array_7_downto_4[7], 0xF0)
    _check_value(tlog, dut.array_7_downto_4[4], 0xC0)
    _check_value(tlog, dut.array_4_to_7[4]    , 0xB0)
    _check_value(tlog, dut.array_4_to_7[7]    , 0x80)
    _check_value(tlog, dut.array_3_downto_0[3], 0x70)
    _check_value(tlog, dut.array_3_downto_0[0], 0x40)
    _check_value(tlog, dut.array_0_to_3[0]    , 0x30)
    _check_value(tlog, dut.array_0_to_3[3]    , 0x00)
    _check_value(tlog, dut.array_0_to_3[1]    , 0x20)

    # Get sub-handles through NonHierarchyIndexableObject.__getitem__
    dut.array_7_downto_4[7] <= 0xDE
    dut.array_4_to_7[4]     <= 0xFC
    dut.array_3_downto_0[0] <= 0xAB
    dut.array_0_to_3[1]     <= 0x7A
    dut.array_0_to_3[3]     <= 0x42

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_7_downto_4[7], 0xDE)
    _check_value(tlog, dut.array_4_to_7[4]    , 0xFC)
    _check_value(tlog, dut.array_3_downto_0[0], 0xAB)
    _check_value(tlog, dut.array_0_to_3[1]    , 0x7A)
    _check_value(tlog, dut.array_0_to_3[3]    , 0x42)

    # Set sub-handle values through NonHierarchyIndexableObject.__setitem__
    dut.array_7_downto_4[7] = 0x77
    dut.array_4_to_7[4]     = 0x44
    dut.array_3_downto_0[0] = 0x00
    dut.array_0_to_3[1]     = 0x11
    dut.array_0_to_3[3]     = 0x33

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_7_downto_4[7], 0x77)
    _check_value(tlog, dut.array_4_to_7[4]    , 0x44)
    _check_value(tlog, dut.array_3_downto_0[0], 0x00)
    _check_value(tlog, dut.array_0_to_3[1]    , 0x11)
    _check_value(tlog, dut.array_0_to_3[3]    , 0x33)


@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl")))
async def test_ndim_array_indexes(dut):
    """Test getting and setting values of multi-dimensional array indexes."""

    cocotb.fork(Clock(dut.clk, 1000, 'ns').start())

    dut.array_2d <= [
        [0xF0, 0xE0, 0xD0, 0xC0],
        [0xB0, 0xA0, 0x90, 0x80]
    ]

    await Timer(1000, 'ns')

    # Check indices
    _check_value(tlog, dut.array_2d[1]    , [0xB0, 0xA0, 0x90, 0x80])
    _check_value(tlog, dut.array_2d[0][31], 0xF0)
    _check_value(tlog, dut.array_2d[1][29], 0x90)
    _check_value(tlog, dut.array_2d[1][28], 0x80)

    # Get sub-handles through NonHierarchyIndexableObject.__getitem__
    dut.array_2d[1]     <= [0xDE, 0xAD, 0xBE, 0xEF]
    dut.array_2d[0][31] <= 0x0F

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_2d[0][31], 0x0F)
    _check_value(tlog, dut.array_2d[0][29], 0xD0)
    _check_value(tlog, dut.array_2d[1][30], 0xAD)
    _check_value(tlog, dut.array_2d[1][28], 0xEF)

    # Set sub-handle values through NonHierarchyIndexableObject.__setitem__
    dut.array_2d[0]     = [0xBA, 0xBE, 0xCA, 0xFE]
    dut.array_2d[1][29] = 0x12

    await Timer(1000, 'ns')

    _check_value(tlog, dut.array_2d[0][31], 0xBA)
    _check_value(tlog, dut.array_2d[0][30], 0xBE)
    _check_value(tlog, dut.array_2d[1]    , [0xDE, 0xAD, 0x12, 0xEF])


@cocotb.test(expect_error=AttributeError if cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl")) else ())
async def test_struct(dut):
    """Test setting and getting values of structs."""
    cocotb.fork(Clock(dut.clk, 1000, 'ns').start())
    dut.inout_if.a_in <= 1
    await Timer(1000, 'ns')
    _check_value(tlog, dut.inout_if.a_in, 1)
    dut.inout_if.a_in <= 0
    await Timer(1000, 'ns')
    _check_value(tlog, dut.inout_if.a_in, 0)


@contextlib.contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type as exc:
        tlog.info("   {} raised as expected: {}".format(exc_type.__name__, exc))
    else:
        raise AssertionError("{} was not raised".format(exc_type.__name__))


@cocotb.test()
async def test_exceptions(dut):
    """Test that correct Exceptions are raised."""
    with assert_raises(TypeError):
        dut.array_7_downto_4 <= (0xF0, 0xE0, 0xD0, 0xC0)
    with assert_raises(TypeError):
        dut.array_4_to_7      = Exception("Exception Object")
    with assert_raises(ValueError):
        dut.array_3_downto_0 <= [0x70, 0x60, 0x50]
    with assert_raises(ValueError):
        dut.array_0_to_3     <= [0x40, 0x30, 0x20, 0x10, 0x00]
