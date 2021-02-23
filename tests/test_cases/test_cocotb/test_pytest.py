# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
""" Tests relating to pytest integration """

import cocotb

# pytest is an optional dependency
try:
    import pytest
except ImportError:
    pytest = None


@cocotb.test(skip=pytest is None)
async def test_assertion_rewriting(dut):
    """ Test that assertion rewriting hooks take effect in cocotb tests """
    try:
        assert 1 != 42
    except AssertionError as e:
        assert "42" in str(e), (
            f"Assertion rewriting seems not to work, message was {e}")
