# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


@cocotb.test
async def x_test(_):
    assert False, "Should not match this test"


y_test_with_suffix_ran = False


@cocotb.test
async def y_test_with_suffix(_):
    global y_test_with_suffix_ran
    y_test_with_suffix_ran = True


@cocotb.test
async def y_test(_):
    assert y_test_with_suffix_ran
