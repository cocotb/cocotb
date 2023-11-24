# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import warnings

import cocotb
from common import MyException


@cocotb.test()
async def test_start_soon_doesnt_start_immediately(_):
    a = 0

    async def increments():
        nonlocal a
        a += 1

    # start_soon doesn't run incremenents() immediately, so "a" is never incremented
    cocotb.start_soon(increments())
    assert a == 0


async def coro():
    raise MyException()


@cocotb.test(expect_error=MyException)
async def test_start_doesnt_keep_running(_):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        # failing task ends the test, but because we have to suspend the current task
        # the next raise is never run again after the test fails because the test coro is not scheduled again
        await cocotb.start(coro())
        raise RuntimeError()
