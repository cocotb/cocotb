# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests of cocotb.regression.TestFactory functionality
"""
import cocotb
from cocotb.regression import TestFactory


testfactory_test_args = set()


async def run_testfactory_test(dut, arg1, arg2, arg3):
    testfactory_test_args.add((arg1, arg2, arg3))

factory = TestFactory(run_testfactory_test)
factory.add_option("arg1", ["a1v1", "a1v2"])
factory.add_option(("arg2", "arg3"), [("a2v1", "a3v1"), ("a2v2", "a3v2")])
factory.generate_tests()


@cocotb.test()
async def test_testfactory_verify_args(dut):
    assert testfactory_test_args == {
        ("a1v1", "a2v1", "a3v1"),
        ("a1v2", "a2v1", "a3v1"),
        ("a1v1", "a2v2", "a3v2"),
        ("a1v2", "a2v2", "a3v2"),
    }
