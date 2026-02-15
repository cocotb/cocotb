# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import logging

import cocotb
from cocotb.handle import LogicArrayObject, LogicObject
from cocotb.triggers import RisingEdge, Timer


@cocotb.test()
async def test_debug_array_vhdl(dut):

    await Timer(1, unit="ns")
    tlog = logging.getLogger("cocotb.test")

    def inspect_signal(signal, signal_name):
        tlog.info(f"Signal name: {signal_name} {type(signal)}")

    inspect_signal(dut.test_a, "dut.test_a")
    assert type(dut.test_a) is LogicArrayObject
    inspect_signal(dut.test_b, "dut.test_b")
    assert type(dut.test_a) is LogicArrayObject

    inspect_signal(dut.test_a[0], "test_a[0]")
    assert type(dut.test_a[0]) is LogicObject

    handle = dut.test_a[0]
    tlog.info(f"dut.test_a[0] Value = {handle.value}")
    await RisingEdge(handle)
