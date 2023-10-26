# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import ctypes
from typing import List

import pytest

import cocotb
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer


# strings are not supported on Icarus (gh-2585) or GHDL (gh-2584)
@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith("icarus")
    else TypeError
    if cocotb.SIM_NAME.lower().startswith("ghdl")
    else ()
)
async def test_unicode_handle_assignment_deprecated(dut):
    with pytest.warns(DeprecationWarning, match=".*bytes.*"):
        dut.stream_in_string.value = "Bad idea"
        await cocotb.triggers.ReadWrite()


@cocotb.test()
async def test_convert_handle_to_string_deprecated(dut):
    dut.stream_in_data.value = 0
    await cocotb.triggers.Timer(1, units="ns")

    with pytest.warns(FutureWarning, match=".*_path.*"):
        as_str = str(dut.stream_in_data)

    # in future this will be ` == dut._path`
    assert as_str == str(dut.stream_in_data.value)

    if cocotb.LANGUAGE == "verilog":
        # the `NUM_OF_MODULES` parameter is only present in the verilog design
        with pytest.warns(FutureWarning, match=".*_path.*"):
            as_str = str(dut.NUM_OF_MODULES)

        # in future this will be ` == dut._path`
        assert as_str == str(dut.NUM_OF_MODULES.value)


@cocotb.test()
async def test_assigning_structure_deprecated(dut):
    """signal.value = ctypes.Structure assignment is deprecated"""

    class Example(ctypes.Structure):
        _fields_ = [("a", ctypes.c_byte), ("b", ctypes.c_uint32)]

    e = Example(a=0xCC, b=0x12345678)

    with pytest.warns(DeprecationWarning):
        dut.stream_in_data_wide.value = e

    await Timer(1, "step")

    assert dut.stream_in_data_wide == BinaryValue(
        value=bytes(e), n_bits=len(dut.stream_in_data_wide)
    )


@cocotb.test()
async def test_time_ps_deprecated(_):
    with pytest.warns(DeprecationWarning):
        Timer(time_ps=7, units="ns")
    with pytest.raises(TypeError):
        Timer(time=0, time_ps=7, units="ns")
    with pytest.raises(TypeError):
        Timer(units="ps")


def pack_bit_vector(values: List[int], bits: int):
    """Pack the integers in `values` into a single integer, with each entry occupying `bits` bits.

    >>> pack_bit_vector([0x012, 0x234, 0x456], bits=12) == 0x456234012
    True
    """
    return sum(v << (bits * i) for i, v in enumerate(values))


@cocotb.test()
async def test_dict_signal_assignment_deprecated(dut):
    """Assigning a dict to a ModifiableObject signal is deprecated"""

    d = dict(values=[0xC, 0x5], bits=4)

    with pytest.warns(DeprecationWarning):
        dut.stream_in_data.value = d

    await Timer(1, "step")

    assert dut.stream_in_data.value == pack_bit_vector(**d)
