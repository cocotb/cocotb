# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests of cocotb.regression.parametrize functionality
"""

from collections.abc import Coroutine

import cocotb

parametrize_test_names = set()
parametrize_test_args = set()


@cocotb.test
@cocotb.parametrize(
    ("arg1", ["a1v1", "a1v2"]), (("arg2", "arg3"), [("a2v1", "a3v1"), ("a2v2", "a3v2")])
)
async def run_parametrize_test(dut, arg1, arg2, arg3):
    parametrize_test_names.add(cocotb._regression_manager._test.name)
    parametrize_test_args.add((arg1, arg2, arg3))


@cocotb.test()
async def test_parametrize_verify_args(dut):
    assert parametrize_test_args == {
        ("a1v1", "a2v1", "a3v1"),
        ("a1v2", "a2v1", "a3v1"),
        ("a1v1", "a2v2", "a3v2"),
        ("a1v2", "a2v2", "a3v2"),
    }


@cocotb.test
async def test_parametrize_verify_names(dut):
    assert parametrize_test_names == {
        "run_parametrize_test/arg1=a1v1/arg2=a2v1/arg3=a3v1",
        "run_parametrize_test/arg1=a1v1/arg2=a2v2/arg3=a3v2",
        "run_parametrize_test/arg1=a1v2/arg2=a2v1/arg3=a3v1",
        "run_parametrize_test/arg1=a1v2/arg2=a2v2/arg3=a3v2",
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


p_parametrize_test_names = set()
p_parametrize_test_args = set()


@cocotb.test()
@cocotb.parametrize(
    arg1=["a1v1", "a1v2"],
    arg2=["a2v1", "a2v2"],
)
async def p_run_parametrize_test(dut, arg1, arg2):
    p_parametrize_test_names.add(cocotb._regression_manager._test.name)
    p_parametrize_test_args.add((arg1, arg2))


@cocotb.test()
async def test_params_verify_args(dut):
    assert p_parametrize_test_args == {
        ("a1v1", "a2v1"),
        ("a1v2", "a2v1"),
        ("a1v1", "a2v2"),
        ("a1v2", "a2v2"),
    }


@cocotb.test
async def test_params_verify_names(dut):
    assert p_parametrize_test_names == {
        "p_run_parametrize_test/arg1=a1v1/arg2=a2v1",
        "p_run_parametrize_test/arg1=a1v1/arg2=a2v2",
        "p_run_parametrize_test/arg1=a1v2/arg2=a2v1",
        "p_run_parametrize_test/arg1=a1v2/arg2=a2v2",
    }


parametrize_no_empty_call_test_args = set()


@cocotb.test
@cocotb.parametrize(
    arg1=["a1v1", "a1v2"],
    arg2=["a2v1", "a2v2"],
)
async def test_parametrize_no_empty_call(dut, arg1, arg2):
    parametrize_no_empty_call_test_args.add((arg1, arg2))


@cocotb.test()
async def test_parametrize_no_empty_call_verify_args(dut):
    assert parametrize_no_empty_call_test_args == {
        ("a1v1", "a2v1"),
        ("a1v2", "a2v1"),
        ("a1v1", "a2v2"),
        ("a1v2", "a2v2"),
    }
