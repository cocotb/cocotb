# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb
from cocotb.handle import ArrayObject, HierarchyArrayObject
from cocotb_tools.sim_versions import VerilatorVersion


@cocotb.test
async def test_sv_if(dut):
    """Test that signals in an interface are discovered"""

    dut.sv_if_i._discover_all()
    assert hasattr(dut.sv_if_i, "a")
    assert hasattr(dut.sv_if_i, "b")
    assert hasattr(dut.sv_if_i, "c")


SIM_NAME = cocotb.SIM_NAME.lower()
verilator_less_than_5024 = SIM_NAME.startswith("verilator") and VerilatorVersion(
    cocotb.SIM_VERSION
) < VerilatorVersion("5.024")


@cocotb.xfail(
    verilator_less_than_5024,
    raises=AttributeError,
    reason="Verilator before 5.024 doesn't support interface arrays (gh-3824)",
)
@cocotb.xfail(
    "vcs" in SIM_NAME,
    raises=AttributeError,
    reason="VCS is unable to access interface arrays",
)
@cocotb.test
async def test_sv_intf_arr_type(dut):
    """Test that interface arrays are the correct type"""

    print(dut.sv_if_arr)

    if cocotb.SIM_NAME.lower().startswith(("xmsim", "modelsim", "riviera")):
        assert isinstance(dut.sv_if_arr, ArrayObject)
    else:
        # This is correct
        assert isinstance(dut.sv_if_arr, HierarchyArrayObject)


@cocotb.xfail(
    verilator_less_than_5024,
    raises=AttributeError,
    reason="Verilator before 5.024 doesn't support interface arrays (gh-3824)",
)
@cocotb.xfail(
    "vcs" in SIM_NAME,
    raises=AttributeError,
    reason="VCS is unable to access interface arrays",
)
@cocotb.xfail(cocotb.SIM_NAME.lower().startswith("riviera"))
@cocotb.test
async def test_sv_intf_arr_len(dut):
    """Test that interface array length is correct"""
    assert len(dut.sv_if_arr) == 3


@cocotb.xfail(
    cocotb.SIM_NAME.lower().startswith("riviera"),
    raises=IndexError,
    reason="Riviera-PRO does not correctly handle interface arrays",
)
@cocotb.xfail(
    verilator_less_than_5024,
    raises=AttributeError,
    reason="Verilator before 5.024 doesn't support interface arrays (gh-3824)",
)
@cocotb.xfail(
    "vcs" in SIM_NAME,
    raises=AttributeError,
    reason="VCS is unable to access interface arrays",
)
@cocotb.test
async def test_sv_intf_arr_access(dut):
    """Test that interface array objects can be accessed"""
    for i in range(3):
        assert hasattr(dut.sv_if_arr[i], "a")
        assert hasattr(dut.sv_if_arr[i], "b")
        assert hasattr(dut.sv_if_arr[i], "c")


@cocotb.xfail(
    verilator_less_than_5024,
    raises=AttributeError,
    reason="Verilator before 5.024 doesn't support interface arrays (gh-3824)",
)
@cocotb.xfail(
    "vcs" in SIM_NAME,
    raises=AttributeError,
    reason="VCS is unable to access interface arrays",
)
@cocotb.xfail(cocotb.SIM_NAME.lower().startswith("riviera"))
@cocotb.test
async def test_sv_intf_arr_iteration(dut):
    """Test that interface arrays can be iterated"""
    count = 0
    for intf in dut.sv_if_arr:
        assert hasattr(intf, "a")
        assert hasattr(intf, "b")
        assert hasattr(intf, "c")
        count += 1

    assert count == 3
