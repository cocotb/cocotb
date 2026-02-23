# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


@cocotb.test()
async def test_architecture_name(dut):
    # This test does not need to do anything to hit this issue.
    pass
