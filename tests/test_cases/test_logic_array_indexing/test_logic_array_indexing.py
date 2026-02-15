# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import os
from typing import Any

import pytest

import cocotb
from cocotb.handle import LogicArrayObject, LogicObject, PackedObject
from cocotb.triggers import RisingEdge, Timer


def inspect_signal(signal: Any, signal_name: str) -> None:
    cocotb.log.info(f"Signal name: {signal_name} {type(signal)}")


TOPLEVEL_LANG = os.getenv("TOPLEVEL_LANG")
assert TOPLEVEL_LANG is not None
TOPLEVEL_LANG = TOPLEVEL_LANG.lower()

SIM = cocotb.SIM_NAME.lower()


@cocotb.test
@cocotb.skipif(
    TOPLEVEL_LANG != "verilog", reason="This test is only applicable to Verilog"
)
async def test_debug_array_verilog(dut: Any) -> None:
    inspect_signal(dut.test_a, "dut.test_a")
    assert type(dut.test_a) is PackedObject

    with pytest.raises(TypeError):
        dut.test_a[0]


@cocotb.test
@cocotb.skipif(TOPLEVEL_LANG != "vhdl", reason="This test is only applicable to VHDL")
@cocotb.xfail(
    SIM.startswith("ghdl"),
    reason="GHDL uses VPI, which does not support array indexing",
)
async def test_debug_array_vhdl(dut: Any) -> None:
    await Timer(1, unit="ns")

    inspect_signal(dut.test_a, "dut.test_a")
    assert type(dut.test_a) is LogicArrayObject
    inspect_signal(dut.test_b, "dut.test_b")
    assert type(dut.test_b) is LogicArrayObject

    inspect_signal(dut.test_a[0], "test_a[0]")
    assert type(dut.test_a[0]) is LogicObject

    handle = dut.test_a[0]
    cocotb.log.info(f"dut.test_a[0] Value = {handle.value}")
    await RisingEdge(handle)
