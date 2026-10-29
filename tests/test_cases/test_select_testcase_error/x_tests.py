# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


@cocotb.test()
async def x_test(dut):
    cocotb.log.info("x_test")
