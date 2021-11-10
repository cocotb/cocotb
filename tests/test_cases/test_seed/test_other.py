# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import cocotb


@cocotb.test()
async def test_pass(_):
    # exists solely so there is another test in another module
    # before the other module is run
    pass
