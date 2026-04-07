# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests the failure path for tests in the regression.py and xunit_reporter.py.

The Makefile in this folder is specially set up to squash any error code due
to a failing test and ensures the failing test is reported properly.
"""

from __future__ import annotations

import cocotb


@cocotb.test()
async def test_fail(_: object) -> None:
    assert False


@cocotb.test(expect_fail=True)
async def test_pass_expect_fail(_: object) -> None:
    assert True


@cocotb.test(expect_error=Exception)
async def test_pass_expect_error(_: object) -> None:
    assert True


@cocotb.test(expect_error=ValueError)
async def test_wrong_error(_: object) -> None:
    raise TypeError


@cocotb.test(expect_fail=True)
async def test_expect_fail_but_errors(_: object) -> None:
    raise Exception()


@cocotb.test
async def test_exception_with_nonprintable_characters(_: object) -> None:
    raise Exception("This is bad! \x00\x0b\x80")


@cocotb.test(expect_error=TypeError)
async def test_expect_error_get_failure(dut: object) -> None:
    assert False


@cocotb.test(expect_error=Exception)
async def test_end_test_with_expect_error(_: object) -> None:
    cocotb.end_test()


@cocotb.test(expect_fail=True)
async def test_end_test_with_expect_fail(_: object) -> None:
    cocotb.end_test()
