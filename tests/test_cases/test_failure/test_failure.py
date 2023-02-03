# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests the failure path for tests in the regression.py and xunit_reporter.py.

The Makefile in this folder is specially set up to squash any error code due
to a failing test and ensures the failing test is reported properly.
"""
import cocotb


@cocotb.test()
async def test_fail(_):
    assert False


@cocotb.test(expect_fail=True)
async def test_pass_expect_fail(_):
    assert True


@cocotb.test(expect_error=Exception)
async def test_pass_expect_error(_):
    assert True


@cocotb.test(expect_error=ValueError)
async def test_wrong_error(_):
    raise TypeError


@cocotb.test(expect_fail=True)
async def test_expect_fail_but_errors(_):
    raise Exception()
