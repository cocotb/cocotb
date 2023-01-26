# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import cocotb


# The purpose of this test is just to complete an elaboration cycle up to time 0, before simulation
# If it fails to get to this point then the addition of the include dirs failed!
@cocotb.test()
async def test_noop(_):
    pass
