# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import cocotb


@cocotb.test()
async def test_sv_if(dut):
    """ Test that signals in an interface are discovered and iterable """

    dut.sv_if_i._discover_all()
    assert hasattr(dut.sv_if_i, 'a')
    assert hasattr(dut.sv_if_i, 'b')
    assert hasattr(dut.sv_if_i, 'c')
