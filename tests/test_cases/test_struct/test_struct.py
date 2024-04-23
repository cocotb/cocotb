# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import contextlib

import cocotb
from cocotb.triggers import Timer

test_dec = cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl", "nvc"))
    else (),
    expect_fail=cocotb.SIM_NAME.lower().startswith(("modelsim", "riviera")),
    skip=cocotb.SIM_NAME.lower().startswith(
        "verilator"
    ),  # verilator already treats packed structs as logic arrays
)


@contextlib.contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type as exc:
        cocotb.log.info(f"   {exc_type.__name__} raised as expected: {exc}")
    else:
        raise AssertionError(f"{exc_type.__name__} was not raised")


@test_dec
async def test_struct_format(dut):
    """Test that the correct objects are returned for a struct"""
    assert repr(dut.my_struct) == "LogicObject(sample_module.my_struct)"

    # use value or value to access signal
    cocotb.log.info(f"dut.my_struct.value={dut.my_struct.value}")
    assert repr(dut.my_struct.value) == "LogicArray('ZZZ', Range(2, 'downto', 0))"


@test_dec
async def test_struct_setting(dut):
    """Test getting and setting setting the value of an entire struct"""

    assert str(dut.my_struct.value) == "ZZZ"

    # test struct write -> individual signals
    dut.my_struct.value = 0
    await Timer(1000, "ns")

    assert str(dut.my_struct.value) == "000"
