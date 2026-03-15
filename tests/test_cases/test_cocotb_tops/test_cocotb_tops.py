# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os

import cocotb

TOPLEVEL_LANG = os.getenv("TOPLEVEL_LANG")
assert TOPLEVEL_LANG is not None
TOPLEVEL_LANG = TOPLEVEL_LANG.lower()

EXPECTED_TOPS_VERILOG = {
    "verilog_top_a",
    "verilog_top_b",
}

EXPECTED_TOPS_VHDL = {
    "vhdl_top_a",
    "vhdl_top_b",
}


@cocotb.test()
@cocotb.skipif(
    TOPLEVEL_LANG != "verilog", reason="This test is only applicable to Verilog"
)
async def test_cocotb_tops_verilog(dut):
    assert hasattr(cocotb, "tops"), "cocotb.tops does not exist"
    assert dut._name == cocotb.top._name

    tops_dict = cocotb.tops
    assert isinstance(tops_dict, dict), "cocotb.tops is not a dict"

    found = set(tops_dict.keys())
    cocotb.log.info(f"Found tops: {found}")

    missing = EXPECTED_TOPS_VERILOG - found
    assert not missing, f"Missing expected tops: {missing}"

    for name in EXPECTED_TOPS_VERILOG:
        handle = tops_dict[name]

        assert handle is not None, f"{name} handle is None"
        assert handle._name == name, f"{name} Handle not Internally resolved properly"


@cocotb.test()
@cocotb.skipif(TOPLEVEL_LANG != "vhdl", reason="This test is only applicable to VHDL")
async def test_cocotb_tops_vhdl(dut):
    assert hasattr(cocotb, "tops"), "cocotb.tops does not exist"
    assert dut._name == cocotb.top._name

    tops_dict = cocotb.tops
    assert isinstance(tops_dict, dict), "cocotb.tops is not a dict"

    found = set(tops_dict.keys())
    cocotb.log.info(f"Found tops: {found}")

    missing = EXPECTED_TOPS_VHDL - found
    assert not missing, f"Missing expected tops: {missing}"

    for name in EXPECTED_TOPS_VHDL:
        handle = tops_dict[name]

        assert handle is not None, f"{name} handle is None"
        assert handle._name == name, f"{name} Handle not Internally resolved properly"
