# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import doctest
import os

import cocotb


@cocotb.test()
async def test_utils(dut):
    # prevent failure in case colored output is requested from the environment
    os.environ['COCOTB_ANSI_OUTPUT'] = "0"
    failures, n = doctest.testmod(cocotb.utils, verbose=True)
    assert failures == 0


@cocotb.test()
async def test_binary(dut):
    failures, n = doctest.testmod(cocotb.binary, verbose=True)
    assert failures == 0
