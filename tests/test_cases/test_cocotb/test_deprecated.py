# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import ctypes
import warnings
from typing import List

import pytest

import cocotb
from cocotb._sim_versions import IcarusVersion
from cocotb.binary import BinaryValue
from cocotb.triggers import Timer


@cocotb.test()
async def test_returnvalue_deprecated(dut):
    @cocotb.coroutine  # testing ReturnValue deprecated
    def get_value():
        yield cocotb.triggers.Timer(1, units="ns")
        raise cocotb.result.ReturnValue(42)

    with pytest.warns(DeprecationWarning, match=".*return statement instead.*"):
        val = await get_value()
    assert val == 42


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
async def test_create_error_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        _ = cocotb.result.create_error(cocotb.triggers.Timer(1), "A test exception")


@cocotb.test()
async def test_raise_error_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        with pytest.raises(cocotb.result.TestError):
            cocotb.result.raise_error(cocotb.triggers.Timer(1), "A test exception")


@cocotb.test()
async def test_handle_compat_mapping(dut):
    """
    Test DeprecationWarnings for _compat_mapping.

    Note that these only warn once per attribute.
    """
    # log
    with pytest.warns(DeprecationWarning):
        dut.log.info("'log' is deprecated")
    # name
    with pytest.warns(DeprecationWarning):
        dut.name = "myname"
    assert dut.name == "myname"
    # fullname
    with pytest.warns(DeprecationWarning):
        dut.fullname = "myfullname"
    assert dut.fullname == "myfullname"


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
async def test_expect_error_bool_deprecated(_):
    async def t():
        pass

    with pytest.warns(DeprecationWarning):
        cocotb.test(expect_error=True)(t)
    with pytest.warns(DeprecationWarning):
        cocotb.test(expect_error=False)(t)


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


@cocotb.test()
async def test_assigning_setattr_syntax_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        dut.stream_in_data = 1
    with pytest.raises(AttributeError):
        # attempt to use __setattr__ syntax on signal that doesn't exist
        dut.does_not_exist = 0


icarus_under_11 = cocotb.SIM_NAME.lower().startswith("icarus") and (
    IcarusVersion(cocotb.SIM_VERSION) <= IcarusVersion("10.3 (stable)")
)


# indexing packed arrays is not supported in iverilog < 11 (gh-2586) or GHDL (gh-2587)
@cocotb.test(
    expect_error=IndexError
    if icarus_under_11 or cocotb.SIM_NAME.lower().startswith("ghdl")
    else ()
)
async def test_assigning_setitem_syntax_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        dut.stream_in_data[0] = 1
    with pytest.warns(DeprecationWarning):
        with pytest.raises(IndexError):
            # attempt to use __setitem__ syntax on signal that doesn't exist
            dut.stream_in_data[800000] = 1


@cocotb.test()
async def test_assigning_less_than_syntax_deprecated(dut):
    with pytest.warns(DeprecationWarning):
        dut.stream_in_data <= 1


@cocotb.test()
async def test_lessthan_raises_error(dut):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ret = dut.stream_in_data <= 0x12
    with pytest.raises(TypeError):
        bool(ret)
