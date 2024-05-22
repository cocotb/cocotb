# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause


import logging
import os
import re

import cocotb
from cocotb._sim_versions import RivieraVersion
from cocotb.triggers import Timer

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test(
    expect_error=(
        AttributeError if SIM_NAME.startswith(("icarus", "ghdl", "nvc")) else ()
    ),
)
async def test_packed_struct_format(dut):
    """Test that the correct objects are returned for a struct"""
    if SIM_NAME.startswith("verilator"):
        assert repr(dut.my_struct) == "LogicObject(sample_module.my_struct)"
    else:
        assert repr(dut.my_struct) == "PackedStructObject(sample_module.my_struct)"
    assert re.fullmatch(
        r"LogicArray\('[0XZ]{3}', Range\(2, 'downto', 0\)\)", repr(dut.my_struct.value)
    )


# Riviera-PRO 2024.04 crashes on this testcase (gh-3936)
sim_ver = RivieraVersion(cocotb.SIM_VERSION)
is_riviera_2024_04 = sim_ver >= "2024.04" and sim_ver < "2024.05"


# Riviera-PRO 2022.10+ ignores writes to the packed struct.
@cocotb.test(
    expect_error=(
        AttributeError if SIM_NAME.startswith(("icarus", "ghdl", "nvc")) else ()
    ),
    expect_fail=(
        SIM_NAME.startswith("riviera")
        and RivieraVersion(cocotb.SIM_VERSION) >= "2022.10"
    ),
    skip=(SIM_NAME.startswith("riviera") and is_riviera_2024_04),
)
async def test_packed_struct_setting(dut):
    """Test setting the value of an entire struct"""

    # test struct write -> individual signals
    dut.my_struct.value = 0
    await Timer(1000, "ns")

    assert str(dut.my_struct.value) == "000"

    # this should be logic length, not children length
    assert len(dut.my_struct) == 3


@cocotb.test(
    expect_error=AttributeError
    if SIM_NAME.startswith(("icarus", "ghdl", "nvc", "verilator", "riviera"))
    else (),
    expect_fail=SIM_NAME.startswith(("modelsim", "riviera")),
)
async def test_packed_struct_internals(dut):
    assert dut.my_struct.val_a.value == 0
    assert dut.my_struct.val_b.value == 0
    assert dut.my_struct["value"].value == 0

    # test logic object fields
    dut.my_struct.set(0)
    dut.my_struct.setimmediatevalue(0)
    assert dut.my_struct.is_const is False

    # test individual signals -> struct

    dut.my_struct.val_a.value = 1
    dut.my_struct["value"].value = 1

    await Timer(1000, "ns")

    assert str(dut.my_struct.value) == "101"
    assert dut.my_struct.val_a.value == 1
    assert dut.my_struct.val_b.value == 0
    assert dut.my_struct["value"].value == 1


# GHDL unable to access record signals (gh-2591)
# Icarus doesn't support structs (gh-2592)
# Verilator doesn't support structs (gh-1275)
# Riviera-PRO does not discover inout_if correctly over VPI (gh-3587, gh-3933)
@cocotb.test(
    expect_error=(
        AttributeError
        if SIM_NAME.startswith(("icarus", "ghdl", "verilator"))
        or (SIM_NAME.startswith("riviera") and LANGUAGE == "verilog")
        else ()
    )
)
async def test_struct_format(dut):
    """
    Access a structure
    """

    tlog = logging.getLogger("cocotb.test")

    structure = dut.inout_if

    tlog.info(
        f"Value of inout_if => a_in = {structure.a_in.value} ; b_out = {structure.b_out.value}"
    )
