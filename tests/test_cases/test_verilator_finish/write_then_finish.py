# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb
from cocotb.triggers import ReadWrite, Timer


@cocotb.test()
async def write_then_finish(dut):
    await Timer(1, "ns")
    await ReadWrite()
    dut.x.value = 1
