# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb


@cocotb.test()
@cocotb.parametrize(a=range(50), b=range(50), c=range(50))
async def parametrize(dut, a, b, c):
    pass
