# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb

@cocotb.test()
async def test_sv_if(dut):
    """ Test that signals in virtual interface are visible """

    dut.sv_if_i.a.value = 1
    dut.sv_if_i.b.value = 1
    dut.sv_if_i.c.value = 1
