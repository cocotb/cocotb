# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
A set of tests that demonstrate package access
"""

import os

import cocotb
from cocotb.handle import (
    HierarchyObject,
    IntegerObject,
    LogicArrayObject,
    StringObject,
)
from cocotb_tools.sim_versions import NvcVersion

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()

questa_vhpi = (
    SIM_NAME.startswith("modelsim") and os.getenv("VHDL_GPI_INTERFACE", "fli") == "vhpi"
)

nvc_pre_1_16 = SIM_NAME.startswith("nvc") and (
    NvcVersion(cocotb.SIM_VERSION) < NvcVersion("1.16")
)


# Riviera-PRO 2019.10 does not detect packages over GPI:
#   AttributeError: 'types.SimpleNamespace' object has no attribute
#   'cocotb_package_pkg_1'
@cocotb.test(
    expect_error=(
        AttributeError
        if (
            cocotb.SIM_NAME.lower().startswith("riviera")
            and cocotb.SIM_VERSION.startswith("2019.10")
        )
        else ()
    ),
    skip=LANGUAGE in ["vhdl"],
)
async def test_package_access_verilog(_) -> None:
    """Test Verilog package parameter access"""

    pkg1 = cocotb.packages.cocotb_package_pkg_1
    assert isinstance(pkg1, HierarchyObject)
    assert pkg1._path.startswith("cocotb_package_pkg_1")

    assert isinstance(pkg1.five_int, LogicArrayObject)
    assert pkg1.five_int._path == "cocotb_package_pkg_1::five_int"
    assert pkg1.five_int.value == 5

    assert isinstance(pkg1.eight_logic, LogicArrayObject)
    assert pkg1.eight_logic._path == "cocotb_package_pkg_1::eight_logic"
    assert pkg1.eight_logic.value == 8

    assert isinstance(pkg1.bit_1_param, LogicArrayObject)
    assert pkg1.bit_1_param._path == "cocotb_package_pkg_1::bit_1_param"
    assert pkg1.bit_1_param.value == 1

    assert isinstance(pkg1.bit_2_param, LogicArrayObject)
    assert pkg1.bit_2_param._path == "cocotb_package_pkg_1::bit_2_param"
    assert pkg1.bit_2_param.value == 3

    assert isinstance(pkg1.bit_600_param, LogicArrayObject)
    assert pkg1.bit_600_param._path == "cocotb_package_pkg_1::bit_600_param"
    assert pkg1.bit_600_param.value == 12345678912345678912345689

    assert isinstance(pkg1.byte_param, LogicArrayObject)
    assert pkg1.byte_param._path == "cocotb_package_pkg_1::byte_param"
    assert pkg1.byte_param.value == 100

    assert isinstance(pkg1.shortint_param, LogicArrayObject)
    assert pkg1.shortint_param._path == "cocotb_package_pkg_1::shortint_param"
    assert pkg1.shortint_param.value == 63000

    assert isinstance(pkg1.int_param, LogicArrayObject)
    assert pkg1.int_param._path == "cocotb_package_pkg_1::int_param"
    assert pkg1.int_param.value == 50

    assert isinstance(pkg1.longint_param, LogicArrayObject)
    assert pkg1.longint_param._path == "cocotb_package_pkg_1::longint_param"
    assert pkg1.longint_param.value == 0x11C98C031CB

    assert isinstance(pkg1.integer_param, LogicArrayObject)
    assert pkg1.integer_param._path == "cocotb_package_pkg_1::integer_param"
    assert pkg1.integer_param.value == 125000

    assert isinstance(pkg1.logic_130_param, LogicArrayObject)
    assert pkg1.logic_130_param._path == "cocotb_package_pkg_1::logic_130_param"
    assert pkg1.logic_130_param.value == 0x8C523EC7DC553A2B

    assert isinstance(pkg1.reg_8_param, LogicArrayObject)
    assert pkg1.reg_8_param._path == "cocotb_package_pkg_1::reg_8_param"
    assert pkg1.reg_8_param.value == 200

    assert isinstance(pkg1.time_param, LogicArrayObject)
    assert pkg1.time_param._path == "cocotb_package_pkg_1::time_param"
    assert pkg1.time_param.value == 0x2540BE400

    pkg2 = cocotb.packages.cocotb_package_pkg_2
    assert isinstance(pkg2, HierarchyObject)
    assert pkg2._path.startswith("cocotb_package_pkg_2")

    assert isinstance(pkg2.eleven_int, LogicArrayObject)
    assert pkg2.eleven_int._path == "cocotb_package_pkg_2::eleven_int"
    assert pkg2.eleven_int.value == 11


# Questa does not implement finding packages via iteration (gh-4693)
# Xcelium does not implement finding packages via iteration (gh-4694)
# GHDL does not implement finding packages via iteration (gh-4695)
@cocotb.test(
    expect_fail=SIM_NAME.startswith(("modelsim", "xmsim", "ghdl")) or nvc_pre_1_16,
    skip=(LANGUAGE in ["verilog"]),
)
async def test_package_access_vhdl(_) -> None:
    """Test VHDL package constant access"""

    assert len(vars(cocotb.packages).keys()) > 0

    pkg1 = cocotb.packages.cocotb_package_pkg_1
    assert isinstance(pkg1, HierarchyObject)

    assert isinstance(pkg1.five_int, IntegerObject)
    assert pkg1.five_int.value == 5

    assert isinstance(pkg1.eight_logic, LogicArrayObject)
    assert pkg1.eight_logic.value == 8

    assert isinstance(pkg1.hello_string, StringObject)
    assert pkg1.hello_string.value == b"hello"


@cocotb.test(skip=(SIM_NAME.startswith("riviera") or LANGUAGE in ["vhdl"]))
async def test_dollar_unit(dut):
    """Test $unit scope"""

    # Is $unit even a package?  Xcelium says yes and 37.10 detail 5 would also suggest yes
    pkgs = vars(cocotb.packages).keys()
    f = filter(lambda x: "unit" in x, pkgs)
    unit = next(iter(f))
    cocotb.log.info(f"Found $unit as {unit}")
    unit_pkg = getattr(cocotb.packages, unit)
    assert unit_pkg.unit_four_int.value == 4


@cocotb.test(expect_error=AttributeError)
async def test_invalid_package(dut):
    """Invalid package name should raise an AttributeError"""
    pkg1 = cocotb.packages.not_here
    assert pkg1 is None
