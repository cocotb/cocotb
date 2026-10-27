# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import os
from typing import Any

import cocotb
from cocotb.clock import Clock
from cocotb.handle import ArrayObject
from cocotb.triggers import ClockCycles

TOPLEVEL_LANG = os.getenv("TOPLEVEL_LANG")
assert TOPLEVEL_LANG is not None
TOPLEVEL_LANG = TOPLEVEL_LANG.lower()


@cocotb.test
async def test_record_multidim_array_indexing(dut: Any) -> None:
    cocotb.start_soon(Clock(dut.pi_clk, 10, "ns").start())
    await ClockCycles(dut.pi_clk, 10)

    # The record field is a 2-D (unpacked) array
    data = dut.po_record_of_array.data
    assert type(data) is ArrayObject, f"Expected ArrayObject, got {type(data)}"

    # One index consumes one dimension -> still a 1-D array
    first_row = data[0]
    assert type(first_row) is ArrayObject, (
        f"Expected ArrayObject, got {type(first_row)}"
    )

    # A second index reaches the leaf element
    elem = first_row[0]
    assert elem.value == 42, f"Expected 42, got {elem.value}"
