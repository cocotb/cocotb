# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import Any

import cocotb
from cocotb_tools.sim_versions import GhdlVersion, VerilatorVersion

LANGUAGE = os.getenv("TOPLEVEL_LANG").lower()
SIM = cocotb.SIM_NAME.lower()


@cocotb.test
@cocotb.skipif(LANGUAGE != "verilog")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed"),
        [
            ("enum", 32, True),
            ("byte", 8, True),
            ("shortint", 16, True),
            ("int", 32, True),
            ("longint", 64, True),
            ("integer", 32, True),
        ],
    )
)
@cocotb.parametrize(obj_type=("input", "signal"))
@cocotb.xfail(
    SIM.startswith("verilator")
    and VerilatorVersion(cocotb.SIM_VERSION) < VerilatorVersion("5.044"),
    reason="Verilator does not support signedness testing before v5.044",
    raises=RuntimeError,
)
async def test_int_verilog(
    verilog_dut: Any, name: str, width: int, is_signed: bool, obj_type: str
) -> None:
    """Test that Verilog integer types are handled correctly."""
    if name == "longint" and obj_type == "input" and SIM.startswith("xmsim"):
        # Xcelium uses different values for VPI constants and this causes longint ports to appear to return vpiRealNet.
        # TODO Replace with pytest.xfail call once supported.
        return
    obj_name = f"{name}_{obj_type}"
    handle = getattr(verilog_dut, obj_name)
    assert len(handle) == width
    assert handle.is_signed is is_signed


@cocotb.test
@cocotb.skipif(LANGUAGE != "vhdl")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed"),
        [
            ("integer", 32, True),
            ("natural", 32, True),
            ("positive", 32, True),
            ("my_integer", 32, True),
        ],
    )
)
@cocotb.parametrize(obj_type=("input", "signal"))
@cocotb.xfail(
    SIM.startswith("ghdl") and GhdlVersion(cocotb.SIM_VERSION) < GhdlVersion("5.2"),
    reason="GHDL does not support signedness testing before 5.2",
)
async def test_integer_access_vhdl(
    vhdl_dut: Any, name: str, width: int, is_signed: bool, obj_type: str
) -> None:
    """Test that VHDL integer types are handled correctly."""
    obj_name = f"{name}_{obj_type}"
    handle = getattr(vhdl_dut, obj_name)
    assert handle.is_signed is is_signed
    assert len(handle) == width
