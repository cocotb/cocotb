# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
A test to demonstrate initial has happened before cocotb is invoked
"""

import logging

import cocotb


@cocotb.test()
async def test_initial(dut):
    """Test that initial has already happened"""
    tlog = logging.getLogger("cocotb.test")

    tlog.info("Checking foo:")
    assert dut.foo.value == 123
