# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
""" Tests relating to pytest integration """

import cocotb
import pytest


@cocotb.test()
async def test_assertion_rewriting(_):
    """ Test that assertion rewriting hooks take effect in cocotb tests """
    with pytest.raises(AssertionError) as e:
        assert 1 == 42
    assert "42" in str(e), f"Assertion rewriting seems not to work, message was {e}"
