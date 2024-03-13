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
    assert repr(dut.my_struct) == "PackedStructObject(sample_module.my_struct)"

    # use value or value to access signal
    cocotb.log.info(f"dut.my_struct.value={dut.my_struct.value}")
    assert repr(dut.my_struct.value) == "LogicArray('ZZZ', Range(2, 'downto', 0))"

    hier_obj = dut.my_struct.asHierarchyObject()
    assert repr(hier_obj) == "HierarchyObject(sample_module.my_struct)"
    cocotb.log.info(f"val_a={hier_obj.val_a.value}")
    assert repr(hier_obj.val_a) == "LogicObject(sample_module.my_struct.val_a)"

    cocotb.log.info(f"val_b={hier_obj.val_b.value}")
    assert repr(hier_obj.val_b) == "LogicObject(sample_module.my_struct.val_b)"


@test_dec
async def test_struct_setting(dut):
    """Test getting and setting setting the value of an entire struct"""

    assert dut.my_struct.value.binstr == "ZZZ"

    # test struct write -> individual signals
    dut.my_struct.value = 0
    await Timer(1000, "ns")

    assert dut.my_struct.value.binstr == "000"

    # check inner signals
    hier_obj = dut.my_struct.asHierarchyObject()
    assert hier_obj.val_a.value == 0
    assert hier_obj.val_b.value == 0

    # test signal write -> struct value
    hier_obj.val_a.value = 1
    await Timer(1000, "ns")
    assert dut.my_struct.value.binstr == "100"

    hier_obj.val_b.value = 1
    await Timer(1000, "ns")
    assert dut.my_struct.value.binstr == "110"
