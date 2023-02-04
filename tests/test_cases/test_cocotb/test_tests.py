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

import pytest
from _pytest.outcomes import Failed
from common import MyBaseException, MyException

import cocotb
from cocotb.triggers import NullTrigger, Timer


@cocotb.test(expect_error=NameError)
async def test_error(dut):
    """Error in the test"""
    await Timer(100, "ns")
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
    """Test that tests can return immediately"""
    return


@cocotb.test(expect_fail=True)
async def test_assertion_is_failure(dut):
    assert False


@cocotb.test(expect_error=MyException)
async def test_expect_particular_exception(dut):
    raise MyException()


@cocotb.test(expect_error=(MyException, ValueError))
async def test_expect_exception_list(dut):
    raise MyException()


@cocotb.test(
    expect_error=cocotb.result.SimTimeoutError, timeout_time=1, timeout_unit="ns"
)
async def test_timeout_testdec_fail(dut):
    await Timer(10, "ns")


@cocotb.test(timeout_time=100, timeout_unit="ns")
async def test_timeout_testdec_pass(dut):
    await Timer(10, "ns")


@cocotb.test(timeout_time=10, timeout_unit="ns")
async def test_timeout_testdec_simultaneous(dut):
    try:
        await cocotb.triggers.with_timeout(
            Timer(1, "ns"), timeout_time=1, timeout_unit="ns"
        )
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


@cocotb.test()
async def test_empty_docstring(dut) -> None:
    """"""


@cocotb.test(expect_error=Failed)
async def test_pytest_raises_fail(dut):
    with pytest.raises(AssertionError):
        assert True


@cocotb.test(expect_error=Failed)
async def test_pytest_warns_fail(dut):
    def test_func():
        pass

    with pytest.warns(RuntimeWarning):
        test_func()


@cocotb.test(expect_error=Failed)
async def test_pytest_deprecated_call_fail(dut):
    def test_func():
        pass

    with pytest.deprecated_call():
        test_func()


@cocotb.test(expect_error=Failed)
async def test_pytest_raises_fail_in_task(dut):
    async def test_func():
        with pytest.raises(AssertionError):
            assert True

    cocotb.start_soon(test_func())
    await NullTrigger()


@cocotb.test(expect_error=Failed)
async def test_pytest_warns_fail_in_task(dut):
    def inner_func():
        pass

    async def test_func():
        with pytest.warns(RuntimeWarning):
            inner_func()

    cocotb.start_soon(test_func())
    await NullTrigger()


@cocotb.test(expect_error=Failed)
async def test_pytest_deprecated_call_fail_in_task(dut):
    def inner_func():
        pass

    async def test_func():
        with pytest.deprecated_call():
            inner_func()

    cocotb.start_soon(test_func())
    await NullTrigger()


@cocotb.test(expect_fail=True)
async def test_pytest_raises_fail_expect_fail(dut):
    with pytest.raises(AssertionError):
        assert True


@cocotb.test(expect_fail=True)
async def test_base_exception_expect_fail(dut):
    raise MyBaseException


@cocotb.test(expect_fail=True)
async def test_base_exception_in_task_expect_fail(dut):
    async def test_func():
        raise MyBaseException

    cocotb.start_soon(test_func())
    await NullTrigger()


@cocotb.test(expect_fail=True)
async def test_exception_expect_fail(dut):
    raise MyException()


@cocotb.test(expect_fail=True)
async def test_exception_in_task_expect_fail(dut):
    async def test_func():
        raise MyException

    cocotb.start_soon(test_func())
    await NullTrigger()
