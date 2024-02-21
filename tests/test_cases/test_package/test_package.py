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
async def test_integer_parameters(dut):
    """Test package integer parameter access"""

    pkg1 = cocotb.packages.cocotb_package_pkg_1

    assert str(pkg1.bit_1_param) == "LogicObject(cocotb_package_pkg_1::bit_1_param)"
    assert pkg1.bit_1_param.value.integer == 1

    assert str(pkg1.bit_2_param) == "LogicObject(cocotb_package_pkg_1::bit_2_param)"
    assert pkg1.bit_2_param.value.integer == 3

    assert str(pkg1.bit_600_param) == "LogicObject(cocotb_package_pkg_1::bit_600_param)"
    assert pkg1.bit_600_param.value.integer == 12345678912345678912345689

    assert str(pkg1.byte_param) == "LogicObject(cocotb_package_pkg_1::byte_param)"
    assert pkg1.byte_param.value.integer == 100

    assert (
        str(pkg1.shortint_param) == "LogicObject(cocotb_package_pkg_1::shortint_param)"
    )
    assert pkg1.shortint_param.value.integer == 63000

    assert str(pkg1.int_param) == "LogicObject(cocotb_package_pkg_1::int_param)"
    assert pkg1.int_param.value.integer == 50

    assert str(pkg1.longint_param) == "LogicObject(cocotb_package_pkg_1::longint_param)"
    assert pkg1.longint_param.value.integer == 0x11C98C031CB

    assert str(pkg1.integer_param) == "LogicObject(cocotb_package_pkg_1::integer_param)"
    assert pkg1.integer_param.value.integer == 125000

    assert (
        str(pkg1.logic_130_param)
        == "LogicObject(cocotb_package_pkg_1::logic_130_param)"
    )
    assert pkg1.logic_130_param.value.integer == 0x8C523EC7DC553A2B

    assert str(pkg1.reg_8_param) == "LogicObject(cocotb_package_pkg_1::reg_8_param)"
    assert pkg1.reg_8_param.value.integer == 200

    assert str(pkg1.time_param) == "LogicObject(cocotb_package_pkg_1::time_param)"
    assert pkg1.time_param.value.integer == 0x2540BE400


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
