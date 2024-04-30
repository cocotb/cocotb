# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import cocotb


@cocotb.test()
async def test_sv_if(dut):
    """Test that signals in an interface are discovered and iterable"""

    dut.sv_if_i._discover_all()
    assert hasattr(dut.sv_if_i, "a")
    assert hasattr(dut.sv_if_i, "b")
    assert hasattr(dut.sv_if_i, "c")


@cocotb.test()
async def test_sv_intf_arr_type(dut):
    """Test that interface arrays are the correct type and iterable"""

    print(dut.sv_if_arr)

    if cocotb.SIM_NAME.lower().startswith("xmsim"):
        assert isinstance(dut.sv_if_arr, cocotb.handle.ArrayObject)
    else:
        # This is correct
        assert isinstance(dut.sv_if_arr, cocotb.handle.HierarchyArrayObject)


@cocotb.test()
async def test_sv_intf_arr_len(dut):
    assert len(dut.sv_if_arr) == 3


@cocotb.test()
async def test_sv_intf_arr_access(dut):
    for i in range(3):
        assert hasattr(dut.sv_if_arr[i], "a")
        assert hasattr(dut.sv_if_arr[i], "b")
        assert hasattr(dut.sv_if_arr[i], "c")


@cocotb.test()
async def test_sv_intf_arr_iteration(dut):
    count = 0
    for intf in dut.sv_if_arr:
        assert hasattr(intf, "a")
        assert hasattr(intf, "b")
        assert hasattr(intf, "c")
        count += 1

    assert count == 3
