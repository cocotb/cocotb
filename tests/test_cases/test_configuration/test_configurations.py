# Copyright cocotb contributors
# Copyright (c) 2015 Potential Ventures Ltd
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


@cocotb.test
async def test_configuration(dut):
    for item in dut.dut_inst:
        cocotb.log.info("Found %r", item)
