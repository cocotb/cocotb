# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""
A test to demonstrate defaultless parameter access
"""

from __future__ import annotations

import logging

import cocotb


@cocotb.test()
async def test_params(dut):
    """Test module parameter access"""
    tlog = logging.getLogger("cocotb.test")

    tlog.info("Checking Parameters:")
    assert dut.the_foo.has_default.value == 2
    assert dut.the_foo.has_no_default.value == 3
