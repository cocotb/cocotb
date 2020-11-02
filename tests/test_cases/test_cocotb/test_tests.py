# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests of cocotb.test functionality

* expect_error
* expect_fail
* timeout
"""
import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestFailure
from common import clock_gen


@cocotb.test(expect_error=True)
def test_syntax_error(dut):
    """Syntax error in the test"""
    yield clock_gen(dut.clk)
    fail  # noqa


@cocotb.test()
def test_tests_are_tests(dut):
    """
    Test that things annotated with cocotb.test are tests
    """
    yield Timer(1)

    assert isinstance(test_tests_are_tests, cocotb.test)


# just to be sure...
@cocotb.test(expect_fail=True)
async def test_async_test_can_fail(dut):
    await Timer(1)
    raise TestFailure  # explicitly do not use assert here


@cocotb.test()
def test_immediate_test(dut):
    """ Test that tests can return immediately """
    return
    yield


@cocotb.test(expect_fail=True)
def test_assertion_is_failure(dut):
    yield Timer(1)
    assert False


class MyException(Exception):
    pass


@cocotb.test(expect_error=MyException)
def test_expect_particular_exception(dut):
    yield Timer(1)
    raise MyException()


@cocotb.test(expect_error=(MyException, ValueError))
def test_expect_exception_list(dut):
    yield Timer(1)
    raise MyException()


@cocotb.test(expect_error=cocotb.result.SimTimeoutError, timeout_time=1, timeout_unit='ns')
def test_timeout_testdec_fail(dut):
    yield Timer(10, 'ns')


@cocotb.test(timeout_time=100, timeout_unit='ns')
def test_timeout_testdec_pass(dut):
    yield Timer(10, 'ns')


@cocotb.test(timeout_time=10, timeout_unit='ns')
def test_timeout_testdec_simultaneous(dut):
    try:
        yield cocotb.triggers.with_timeout(Timer(1, 'ns'), timeout_time=1, timeout_unit='ns')
    except cocotb.result.SimTimeoutError:
        pass
    else:
        assert False, "Expected a Timeout"
    # Whether this test fails or passes depends on the behavior of the
    # scheduler, simulator, and the implementation of the timeout function.
    # CAUTION: THIS MAY CHANGE


# these tests should run in definition order, not lexicographic order
last_ordered_test = None


@cocotb.test()
async def test_ordering_3(dut):
    global last_ordered_test
    val, last_ordered_test = last_ordered_test, 3
    assert val is None


@cocotb.test()
async def test_ordering_2(dut):
    global last_ordered_test
    val, last_ordered_test = last_ordered_test, 2
    assert val == 3


@cocotb.test()
async def test_ordering_1(dut):
    global last_ordered_test
    val, last_ordered_test = last_ordered_test, 1
    assert val == 2
