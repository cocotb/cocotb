# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :py:func:`cocotb.pass_test`."""

from __future__ import annotations

import cocotb


async def test_pass(dut) -> None:
    """Test :py:func:`cocotb.pass_test`."""
    cocotb.pass_test()

    assert False, "this should never be reached"
