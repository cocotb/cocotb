# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests of cocotb.test functionality

* expect_error
* expect_fail
* timeout
"""
from collections.abc import Coroutine

import cocotb
from cocotb.triggers import Timer
from common import clock_gen


@cocotb.test(expect_error=NameError)
async def test_error(dut):
    """Error in the test"""
    await clock_gen(dut.clk)
    fail  # noqa


@cocotb.test()
async def test_tests_are_tests(dut):
    """
    Test that things annotated with cocotb.test are tests
    """
    assert isinstance(test_tests_are_tests, cocotb.test)


# just to be sure...
@cocotb.test(expect_fail=True)
async def test_async_test_can_fail(dut):
    assert False


@cocotb.test()
async def test_immediate_test(dut):
    """ Test that tests can return immediately """
    return


@cocotb.test(expect_fail=True)
async def test_assertion_is_failure(dut):
    assert False


class MyException(Exception):
    pass


@cocotb.test(expect_error=MyException)
async def test_expect_particular_exception(dut):
    raise MyException()


@cocotb.test(expect_error=(MyException, ValueError))
async def test_expect_exception_list(dut):
    raise MyException()


@cocotb.test(expect_error=cocotb.result.SimTimeoutError, timeout_time=1, timeout_unit='ns')
async def test_timeout_testdec_fail(dut):
    await Timer(10, 'ns')


@cocotb.test(timeout_time=100, timeout_unit='ns')
async def test_timeout_testdec_pass(dut):
    await Timer(10, 'ns')


@cocotb.test(timeout_time=10, timeout_unit='ns')
async def test_timeout_testdec_simultaneous(dut):
    try:
        await cocotb.triggers.with_timeout(Timer(1, 'ns'), timeout_time=1, timeout_unit='ns')
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


@cocotb.test()
class TestClass(Coroutine):

    def __init__(self, dut):
        self._coro = self.run(dut)

    async def run(self, dut):
        pass

    def send(self, value):
        self._coro.send(value)

    def throw(self, exception):
        self._coro.throw(exception)

    def __await__(self):
        yield from self._coro.__await__()
