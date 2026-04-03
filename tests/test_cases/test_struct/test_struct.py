# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import os
import re

import cocotb
from cocotb.triggers import Timer
from cocotb_tools.sim_versions import RivieraVersion

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()


@cocotb.test
@cocotb.xfail(
    SIM_NAME.startswith("icarus"),
    raises=AttributeError,
    reason="Icarus does not support structs (gh-2592)",
)
@cocotb.xfail(
    SIM_NAME.startswith("verilator"),
    reason="Verilator finds packed structs as HierarchyObjects (gh-5477)",
)
async def test_packed_struct_format(dut):
    """Test that the correct objects are returned for a struct"""
    assert repr(dut.my_struct) == "PackedStructObject(sample_module.my_struct)"

    # Riviera-PRO initializes the struct with X, Verilator with 0, and others
    # with Z. Since we don't want to explicitly set dut.my_struct (write tests
    # are below) we accept any initialization the simulator might choose.
    assert re.fullmatch(
        r"LogicArray\('[0XZ]{3}', Range\(2, 'downto', 0\)\)", repr(dut.my_struct.value)
    )


# Riviera-PRO 2024.04 crashes on this testcase (gh-3936)
sim_ver = RivieraVersion(cocotb.SIM_VERSION)
is_riviera_2024_04 = (
    sim_ver >= "2024.04" and sim_ver < "2024.05"
    if SIM_NAME.startswith("riviera")
    else None
)


@cocotb.test
@cocotb.xfail(
    SIM_NAME.startswith("icarus"),
    raises=AttributeError,
    reason="Icarus does not support structs (gh-2592)",
)
@cocotb.xfail(
    SIM_NAME.startswith("riviera")
    and RivieraVersion(cocotb.SIM_VERSION) >= "2022.10"
    and RivieraVersion(cocotb.SIM_VERSION) < "2024.10",
    reason="Riviera-PRO 2022.10 - 2023.10 ignores writes to the packed struct",
)
@cocotb.skipif(
    SIM_NAME.startswith("riviera") and is_riviera_2024_04,
    reason="Riviera-PRO 2024.04 crashes on this testcase",
)
async def test_packed_struct_setting(dut):
    """Test setting the value of an entire struct"""

    # test struct write -> individual signals
    dut.my_struct.value = 0
    await Timer(1000, "ns")

    assert str(dut.my_struct.value) == "000"


@cocotb.test(
    expect_error=(
        AttributeError
        if SIM_NAME.startswith(("icarus", "ghdl", "verilator")) or ()
        else ()
    )
)
@cocotb.xfail(
    SIM_NAME.startswith("icarus"),
    raises=AttributeError,
    reason="Icarus does not support structs (gh-2592)",
)
@cocotb.xfail(
    SIM_NAME.startswith("verilator"),
    raises=AttributeError,
    reason="Verilator does not support structs (gh-5477)",
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
