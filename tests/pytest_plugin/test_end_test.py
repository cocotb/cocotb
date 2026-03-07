# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :py:func:`cocotb.end_test`."""

from __future__ import annotations

import cocotb


async def test_end_test(dut) -> None:
    """Test :py:func:`cocotb.end_test`."""
    cocotb.end_test()
    assert False, "this should never be reached"
