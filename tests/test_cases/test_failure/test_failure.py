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


@cocotb.test()
async def test_fail_test_forces_fail(_: object) -> None:
    # A forced failure must record the test as FAIL even though nothing raised
    # through the test coroutine itself (the out-of-context use case).
    cocotb.fail_test("failed by request")


@cocotb.test()
async def test_fail_test_with_custom_exc(_: object) -> None:
    # The caller's exception is attached as the failure cause.
    try:
        raise RuntimeWarning("warning promoted to failure")
    except RuntimeWarning as w:
        cocotb.fail_test("warning promoted to failure", exc=w)


@cocotb.test(expect_fail=True)
async def test_fail_test_overrides_expect_fail(_: object) -> None:
    # fail_test precedence: the forced failure is not converted to an xfail
    # by expect_fail (mirroring pass_test's precedence over xfail).
    cocotb.fail_test("forced failure with expect_fail set")


@cocotb.test()
async def test_fail_regression_fails_this_test(_: object) -> None:
    # The running test is failed immediately...
    cocotb.fail_regression("regression failed by request")


@cocotb.test()
async def test_fail_regression_fails_remaining_tests(_: object) -> None:
    # ...and this test is never run: _execute() scores it as failed because
    # _regression_terminated was set by the call above.
    assert False, "this test must be scored as failed without running"
