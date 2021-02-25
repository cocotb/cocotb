# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import cocotb
from cocotb.triggers import Timer
from cocotb.binary import BinaryValue
import warnings
import ctypes
from contextlib import contextmanager
from common import assert_raises


@contextmanager
def assert_deprecated(warning_category=DeprecationWarning):
    warns = []
    try:
        with warnings.catch_warnings(record=True) as warns:
            # Cause all warnings to always be triggered.
            warnings.simplefilter("always")
            yield warns  # note: not a cocotb yield, but a contextlib one!
    finally:
        assert len(warns) >= 1
        msg = "Expected {}".format(warning_category.__qualname__)
        assert issubclass(warns[0].category, warning_category), msg


@cocotb.test()
async def test_returnvalue_deprecated(dut):

    @cocotb.coroutine   # testing ReturnValue deprecated
    def get_value():
        yield cocotb.triggers.Timer(1, units='ns')
        raise cocotb.result.ReturnValue(42)

    with assert_deprecated() as warns:
        val = await get_value()
    assert val == 42
    assert "return statement instead" in str(warns[0].message)


# strings are not supported on Icarus
@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith("icarus"))
async def test_unicode_handle_assignment_deprecated(dut):
    with assert_deprecated() as warns:
        dut.stream_in_string <= "Bad idea"
        await cocotb.triggers.ReadWrite()
    assert "bytes" in str(warns[0].message)


@cocotb.test()
async def test_convert_handle_to_string_deprecated(dut):
    dut.stream_in_data <= 0
    await cocotb.triggers.Timer(1, units='ns')

    with assert_deprecated(FutureWarning) as warns:
        as_str = str(dut.stream_in_data)
    assert "_path" in str(warns[0].message)

    # in future this will be ` == dut._path`
    assert as_str == str(dut.stream_in_data.value)

    if cocotb.LANGUAGE == "verilog":
        # the `NUM_OF_MODULES` parameter is only present in the verilog design
        with assert_deprecated(FutureWarning) as warns:
            as_str = str(dut.NUM_OF_MODULES)

        assert "_path" in str(warns[0].message)

        # in future this will be ` == dut._path`
        assert as_str == str(dut.NUM_OF_MODULES.value)


@cocotb.test()
async def test_create_error_deprecated(dut):
    with assert_deprecated():
        _ = cocotb.result.create_error(cocotb.triggers.Timer(1), "A test exception")


@cocotb.test()
async def test_raise_error_deprecated(dut):
    with assert_deprecated():
        with assert_raises(cocotb.result.TestError):
            cocotb.result.raise_error(cocotb.triggers.Timer(1), "A test exception")


@cocotb.test()
async def test_hook_deprecated(_):
    async def example():
        pass
    with assert_deprecated():
        cocotb.hook()(example)


@cocotb.test()
async def test_handle_compat_mapping(dut):
    """
    Test DeprecationWarnings for _compat_mapping.

    Note that these only warn once per attribute.
    """
    # log
    with assert_deprecated():
        dut.log.info("'log' is deprecated")
    # name
    with assert_deprecated():
        dut.name = "myname"
    assert dut.name == "myname"
    # fullname
    with assert_deprecated():
        dut.fullname = "myfullname"
    assert dut.fullname == "myfullname"


@cocotb.test()
async def test_assigning_structure_deprecated(dut):
    """signal <= ctypes.Structure assignment is deprecated"""

    class Example(ctypes.Structure):
        _fields_ = [
            ("a", ctypes.c_byte),
            ("b", ctypes.c_uint32)]

    e = Example(a=0xCC, b=0x12345678)

    with assert_deprecated():
        dut.stream_in_data_wide <= e

    await Timer(1, 'step')

    assert dut.stream_in_data_wide == BinaryValue(value=bytes(e), n_bits=len(dut.stream_in_data_wide))


@cocotb.test()
async def test_expect_error_bool_deprecated(_):
    async def t():
        pass
    with assert_deprecated():
        cocotb.test(expect_error=True)(t)
    with assert_deprecated():
        cocotb.test(expect_error=False)(t)


@cocotb.test()
async def test_time_ps_deprecated(_):
    with assert_deprecated():
        Timer(time_ps=7, units='ns')
    with assert_raises(TypeError):
        Timer(time=0, time_ps=7, units='ns')
    with assert_raises(TypeError):
        Timer(units='ps')


@cocotb.test()
async def test_value_assignment_truncation_deprecated(dut):
    with assert_deprecated(FutureWarning):
        # value too large to fit, will cause truncation
        dut.stream_in_data <= 0x12345678
