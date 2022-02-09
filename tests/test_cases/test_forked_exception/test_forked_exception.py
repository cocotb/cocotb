# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Tests the failure path for tests in the regression.py and xunit_reporter.py.

The Makefile in this folder is specially set up to squash any error code due
to a failing test and ensures the failing test is reported properly.
"""
import warnings

import cocotb
from cocotb.triggers import Timer

warnings.simplefilter("error", category=FutureWarning)


class MyException(Exception):
    ...


@cocotb.test(expect_error=MyException)
async def test_fail(_):
    async def fails():
        await Timer(10, "ns")
        raise MyException

    cocotb.fork(fails())
    await Timer(20, "ns")
