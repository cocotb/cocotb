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
    assert repr(dut.inout_if) == "PackedStructObject(sample_module.inout_if)"

    # use value or value to access signal
    cocotb.log.info(f"dut.inout_if.value={dut.inout_if.value}")
    assert repr(dut.inout_if.value) == "LogicArray('ZZ', Range(1, 'downto', 0))"

    hier_obj = dut.inout_if.asHierarchyObject()
    assert repr(hier_obj) == "HierarchyObject(sample_module.inout_if)"
    cocotb.log.info(f"a_in={hier_obj.a_in.value}")
    assert repr(hier_obj.a_in) == "LogicObject(sample_module.inout_if.a_in)"

    cocotb.log.info(f"b_out={hier_obj.b_out.value}")
    assert repr(hier_obj.b_out) == "LogicObject(sample_module.inout_if.b_out)"


@test_dec
async def test_struct_setting(dut):
    """Test getting and setting setting the value of an entire struct"""

    assert dut.inout_if.value.binstr == "ZZ"

    # test struct write -> individual signals
    dut.inout_if.value = 0
    await Timer(1000, "ns")

    assert dut.inout_if.value.binstr == "00"

    # check inner signals
    hier_obj = dut.inout_if.asHierarchyObject()
    assert hier_obj.a_in.value == 0
    assert hier_obj.b_out.value == 0

    # test signal write -> struct value
    hier_obj.a_in.value = 1
    await Timer(1000, "ns")
    assert dut.inout_if.value.binstr == "10"

    hier_obj.b_out.value = 1
    await Timer(1000, "ns")
    assert dut.inout_if.value.binstr == "11"
