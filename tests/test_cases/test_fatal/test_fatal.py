# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb
from cocotb.regression import SimFailure
from cocotb.triggers import Timer


@cocotb.xfail(raises=SimFailure)
@cocotb.test
async def test_fatal(_):
    await Timer(100, "ns")
