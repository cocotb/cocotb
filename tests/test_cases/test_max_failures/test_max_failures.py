# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb
from cocotb.regression import RegressionTerminated


@cocotb.test
async def test_max_failures(dut: object) -> None:
    """Test that the test fails after the first failure when COCOTB_MAX_FAILURES is set to 1."""
    assert False, "This test should fail immediately due to max failures limit."


@cocotb.test(expect_error=RegressionTerminated)
async def test_should_not_run(dut: object) -> None:
    """This test should not run because the previous test should have already caused the test suite to fail."""
