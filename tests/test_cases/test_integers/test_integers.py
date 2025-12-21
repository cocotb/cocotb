# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import Any

import cocotb

LANGUAGE = os.getenv("TOPLEVEL_LANG").lower()


@cocotb.test
@cocotb.skipif(LANGUAGE != "verilog")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed"),
        [
            ("byte_", 8, True),
            ("shortint_", 16, True),
            ("int_", 32, True),
            ("longint_", 64, True),
            ("integer_", 32, True),
        ],
    )
)
async def test_int_verilog(
    verilog_dut: Any, name: str, width: int, is_signed: bool
) -> None:
    """Test that Verilog shortint types are handled correctly."""
    handle = getattr(verilog_dut, name)
    assert len(handle) == width
    assert handle.is_signed is is_signed


@cocotb.test
@cocotb.skipif(LANGUAGE != "vhdl")
@cocotb.parametrize(
    (
        ("name", "width", "is_signed"),
        [
            ("integer_sig", 32, True),
            ("natural_sig", 32, False),
            ("positive_sig", 32, False),
        ],
    )
)
async def test_integer_access_vhdl(
    vhdl_dut: Any, name: str, width: int, is_signed: bool
) -> None:
    """Test that VHDL integer types are handled correctly."""
    handle = getattr(vhdl_dut, name)
    assert len(handle) == width
    assert handle.is_signed is is_signed
