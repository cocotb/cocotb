# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import doctest

import cocotb


@cocotb.test()
async def test_utils(dut):
    failures, n = doctest.testmod(cocotb.utils, verbose=True)
    assert failures == 0


@cocotb.test()
async def test_binary(dut):
    failures, n = doctest.testmod(cocotb.binary, verbose=True)
    assert failures == 0
