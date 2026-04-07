# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


@cocotb.test()
async def y_test(dut):
    pass


@cocotb.test()
async def y_test_with_additional(_):
    assert False, "COCOTB_TESTCASE shouldn't match this test"
