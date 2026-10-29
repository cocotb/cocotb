# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


@cocotb.test()
async def test_start_soon_doesnt_start_immediately(_):
    a = 0

    async def increments():
        nonlocal a
        a += 1

    # start_soon doesn't run incremenents() immediately, so "a" is never incremented
    cocotb.start_soon(increments())
    assert a == 0
