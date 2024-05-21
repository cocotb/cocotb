# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import cocotb


@cocotb.test()
async def test_sv_if(dut):
    """Test that signals in an interface are discovered"""

    dut.sv_if_i._discover_all()
    assert hasattr(dut.sv_if_i, "a")
    assert hasattr(dut.sv_if_i, "b")
    assert hasattr(dut.sv_if_i, "c")


@cocotb.test()
async def test_sv_intf_arr_type(dut):
    """Test that interface arrays are the correct type"""

    print(dut.sv_if_arr)

    if cocotb.SIM_NAME.lower().startswith(("xmsim", "modelsim", "riviera")):
        assert isinstance(dut.sv_if_arr, cocotb.handle.ArrayObject)
    else:
        # This is correct
        assert isinstance(dut.sv_if_arr, cocotb.handle.HierarchyArrayObject)


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith("riviera"))
async def test_sv_intf_arr_len(dut):
    """Test that interface array length is correct"""
    assert len(dut.sv_if_arr) == 3


@cocotb.test(
    expect_error=IndexError if cocotb.SIM_NAME.lower().startswith("riviera") else ()
)
async def test_sv_intf_arr_access(dut):
    """Test that interface array objects can be accessed"""
    for i in range(3):
        assert hasattr(dut.sv_if_arr[i], "a")
        assert hasattr(dut.sv_if_arr[i], "b")
        assert hasattr(dut.sv_if_arr[i], "c")


@cocotb.test(expect_fail=cocotb.SIM_NAME.lower().startswith("riviera"))
async def test_sv_intf_arr_iteration(dut):
    """Test that interface arrays can be iterated"""
    count = 0
    for intf in dut.sv_if_arr:
        assert hasattr(intf, "a")
        assert hasattr(intf, "b")
        assert hasattr(intf, "c")
        count += 1

    assert count == 3
