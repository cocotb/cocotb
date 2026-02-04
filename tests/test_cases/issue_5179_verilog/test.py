# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import logging

import cocotb
from cocotb.handle import ArrayObject, PackedObject


@cocotb.test()
async def test_debug_array_verilog(dut):
    tlog = logging.getLogger("cocotb.test")

    def inspect_signal(signal, signal_name="name"):
        tlog.info(f"Signal name: {signal_name} {type(signal)}")

    inspect_signal(dut.test_a)
    assert type(dut.test_a) is PackedObject
    inspect_signal(dut.test_b)
    assert type(dut.test_b) is ArrayObject

    try:
        dut.test_a[0]
    except TypeError:
        tlog.info("Packed Object indexing failed as expected")
    else:
        raise AssertionError("Verilog packed vector should not be indexable")
