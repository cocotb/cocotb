# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests of cocotb.regression.TestFactory functionality
"""

from collections.abc import Coroutine

import cocotb

testfactory_test_names = set()
testfactory_test_args = set()


@cocotb.test
@cocotb.parametrize(
    ("arg1", ["a1v1", "a1v2"]), (("arg2", "arg3"), [("a2v1", "a3v1"), ("a2v2", "a3v2")])
)
async def run_testfactory_test(dut, arg1, arg2, arg3):
    testfactory_test_names.add(cocotb._regression_manager._test.name)
    testfactory_test_args.add((arg1, arg2, arg3))


@cocotb.test()
async def test_testfactory_verify_args(dut):
    assert testfactory_test_args == {
        ("a1v1", "a2v1", "a3v1"),
        ("a1v2", "a2v1", "a3v1"),
        ("a1v1", "a2v2", "a3v2"),
        ("a1v2", "a2v2", "a3v2"),
    }


@cocotb.test
async def test_testfactory_verify_names(dut):
    assert testfactory_test_names == {
        "run_testfactory_test/arg1=a1v1/arg2=a2v1/arg3=a3v1",
        "run_testfactory_test/arg1=a1v1/arg2=a2v2/arg3=a3v2",
        "run_testfactory_test/arg1=a1v2/arg2=a2v1/arg3=a3v1",
        "run_testfactory_test/arg1=a1v2/arg2=a2v2/arg3=a3v2",
    }


@cocotb.test
@cocotb.parametrize(myarg=[1])
class TestClass(Coroutine):
    def __init__(self, dut, myarg):
        self._coro = self.run(dut, myarg)

    async def run(self, dut, myarg):
        assert myarg == 1

    def send(self, value):
        self._coro.send(value)

    def throw(self, exception):
        self._coro.throw(exception)

    def __await__(self):
        yield from self._coro.__await__()


p_testfactory_test_names = set()
p_testfactory_test_args = set()


@cocotb.test()
@cocotb.parametrize(
    arg1=["a1v1", "a1v2"],
    arg2=["a2v1", "a2v2"],
)
async def p_run_testfactory_test(dut, arg1, arg2):
    p_testfactory_test_names.add(cocotb._regression_manager._test.name)
    p_testfactory_test_args.add((arg1, arg2))


@cocotb.test()
async def test_params_verify_args(dut):
    assert p_testfactory_test_args == {
        ("a1v1", "a2v1"),
        ("a1v2", "a2v1"),
        ("a1v1", "a2v2"),
        ("a1v2", "a2v2"),
    }


@cocotb.test
async def test_params_verify_names(dut):
    assert p_testfactory_test_names == {
        "p_run_testfactory_test/arg1=a1v1/arg2=a2v1",
        "p_run_testfactory_test/arg1=a1v1/arg2=a2v2",
        "p_run_testfactory_test/arg1=a1v2/arg2=a2v1",
        "p_run_testfactory_test/arg1=a1v2/arg2=a2v2",
    }


testfactory_no_empty_call_test_args = set()


@cocotb.test
@cocotb.parametrize(
    arg1=["a1v1", "a1v2"],
    arg2=["a2v1", "a2v2"],
)
async def test_testfactory_no_empty_call(dut, arg1, arg2):
    testfactory_no_empty_call_test_args.add((arg1, arg2))


@cocotb.test()
async def test_testfactory_no_empty_call_verify_args(dut):
    assert testfactory_no_empty_call_test_args == {
        ("a1v1", "a2v1"),
        ("a1v2", "a2v1"),
        ("a1v1", "a2v2"),
        ("a1v2", "a2v2"),
    }
