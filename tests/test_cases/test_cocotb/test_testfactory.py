# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests of cocotb.regression.TestFactory functionality
"""
import random
import string
from collections.abc import Coroutine

import cocotb
from cocotb.regression import TestFactory
from cocotb.triggers import NullTrigger

testfactory_test_names = set()
testfactory_test_args = set()
prefix = "".join(random.choices(string.ascii_letters, k=4))
postfix = "".join(random.choices(string.ascii_letters, k=4))


async def run_testfactory_test(dut, arg1, arg2, arg3):
    testfactory_test_names.add(cocotb.regression_manager._test.__qualname__)
    testfactory_test_args.add((arg1, arg2, arg3))


factory = TestFactory(run_testfactory_test)
factory.add_option("arg1", ["a1v1", "a1v2"])
factory.add_option(("arg2", "arg3"), [("a2v1", "a3v1"), ("a2v2", "a3v2")])
factory.generate_tests(prefix=prefix, postfix=postfix)


@cocotb.test()
async def test_testfactory_verify_args(dut):
    assert testfactory_test_args == {
        ("a1v1", "a2v1", "a3v1"),
        ("a1v2", "a2v1", "a3v1"),
        ("a1v1", "a2v2", "a3v2"),
        ("a1v2", "a2v2", "a3v2"),
    }
    assert testfactory_test_names == {
        f"{prefix}run_testfactory_test{postfix}_{i:03}" for i in range(1, 5)
    }


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


tf = TestFactory(TestClass)
tf.add_option("myarg", [1])
tf.generate_tests()


generator_testfactory_args = set()


@cocotb.coroutine
def generator_test(dut, arg):
    generator_testfactory_args.add(arg)
    yield NullTrigger()


generator_testfactory = TestFactory(generator_test)
generator_testfactory.add_option("arg", [1, 2, 3, 4])
generator_testfactory.generate_tests()


@cocotb.test()
async def test_generator_testfactory(_):
    assert generator_testfactory_args == {1, 2, 3, 4}
