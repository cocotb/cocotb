# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Common utilities shared my many tests in this directory
"""
import re
import traceback
from contextlib import contextmanager

import cocotb
from cocotb.result import TestFailure
from cocotb.triggers import Timer


@cocotb.coroutine
def clock_gen(clock):
    """Example clock gen for test use"""
    for i in range(5):
        clock <= 0
        yield Timer(100)
        clock <= 1
        yield Timer(100)
    clock._log.warning("Clock generator finished!")


@cocotb.coroutine
def _check_traceback(running_coro, exc_type, pattern):
    try:
        yield running_coro
    except exc_type:
        tb_text = traceback.format_exc()
    else:
        raise TestFailure("Exception was not raised")

    if not re.match(pattern, tb_text):
        raise TestFailure(
            (
                "Traceback didn't match - got:\n\n"
                "{}\n"
                "which did not match the pattern:\n\n"
                "{}"
            ).format(tb_text, pattern)
        )


@contextmanager
def assert_raises(exc_type):
    try:
        yield
    except exc_type:
        pass
    else:
        raise AssertionError("{} was not raised".format(exc_type.__name__))
