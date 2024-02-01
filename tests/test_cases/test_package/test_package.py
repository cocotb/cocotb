# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
A set of tests that demonstrate package access
"""

import logging

import cocotb
from cocotb.result import TestSuccess


@cocotb.test()
async def test_params(dut):
    """Test package parameter access"""
    tlog = logging.getLogger("cocotb.test")

    tlog.info("Checking Parameters:")
    assert dut.seven_int.value == 7
    pkg1 = cocotb.packages.cocotb_package_pkg_1
    assert pkg1.five_int.value == 5
    assert pkg1.eight_logic.value == 8
    pkg2 = cocotb.packages.cocotb_package_pkg_2
    assert pkg2.eleven_int.value == 11


@cocotb.test()
async def test_stringification(dut):
    """Test package stringification"""
    tlog = logging.getLogger("cocotb.test")

    tlog.info("Checking Strings:")
    pkg1 = cocotb.packages.cocotb_package_pkg_1
    assert str(pkg1).startswith("HierarchyObject(cocotb_package_pkg_1")
    assert str(pkg1.five_int) == "LogicObject(cocotb_package_pkg_1::five_int)"
    assert str(pkg1.eight_logic) == "LogicObject(cocotb_package_pkg_1::eight_logic)"
    pkg2 = cocotb.packages.cocotb_package_pkg_2
    assert str(pkg2).startswith("HierarchyObject(cocotb_package_pkg_2")
    assert str(pkg2.eleven_int) == "LogicObject(cocotb_package_pkg_2::eleven_int)"


@cocotb.test()
async def test_dollar_unit(dut):
    """Test $unit scope"""
    tlog = logging.getLogger("cocotb.test")

    if cocotb.SIM_NAME.lower().startswith("riviera"):
        tlog.info("Riviera does not support $unit access via vpiInstance")
        raise TestSuccess

    tlog.info("Checking $unit:")
    # Is $unit even a package?  Xcelium says yes and 37.10 detail 5 would also suggest yes
    pkgs = vars(cocotb.packages).keys()
    f = filter(lambda x: "unit" in x, pkgs)
    unit = list(f)[0]
    tlog.info(f"Found $unit as {unit}")
    unit_pkg = getattr(cocotb.packages, unit)
    assert unit_pkg.unit_four_int.value == 4
