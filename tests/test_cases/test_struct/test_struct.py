# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


import cocotb
from cocotb.triggers import Timer

EXPECT_VAL = "000" if cocotb.SIM_NAME.lower().startswith("verilator") else "ZZZ"


@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl", "nvc"))
    else (),
    expect_fail=cocotb.SIM_NAME.lower().startswith(("modelsim", "riviera")),
)
async def test_struct_format(dut):
    """Test that the correct objects are returned for a struct"""
    assert repr(dut.my_struct) == "LogicObject(sample_module.my_struct)"

    # use value or value to access signal
    cocotb.log.info("dut.my_struct.value=%s", dut.my_struct.value)
    assert (
        repr(dut.my_struct.value)
        == f"LogicArray('{EXPECT_VAL}', Range(2, 'downto', 0))"
    )


@cocotb.test(
    expect_error=AttributeError
    if cocotb.SIM_NAME.lower().startswith(("icarus", "ghdl", "nvc"))
    else (),
    expect_fail=cocotb.SIM_NAME.lower().startswith(("modelsim", "riviera")),
)
async def test_struct_setting(dut):
    """Test getting and setting setting the value of an entire struct"""

    assert str(dut.my_struct.value) == EXPECT_VAL

    # test struct write -> individual signals
    dut.my_struct.value = 0
    await Timer(1000, "ns")

    assert str(dut.my_struct.value) == "000"
