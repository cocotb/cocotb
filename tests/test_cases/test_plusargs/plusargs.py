# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
plusarg testing
"""

from __future__ import annotations

import cocotb


@cocotb.test()
async def plusargs_test(dut):
    """Demonstrate plusarg access from Python test"""

    for name in cocotb.plusargs:
        print("COCOTB:", name, cocotb.plusargs[name])

    assert "test1" in cocotb.plusargs
    assert cocotb.plusargs["foo"] == "bar"
    assert cocotb.plusargs["lol"] == "wow=4"
