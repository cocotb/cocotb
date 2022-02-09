# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Common utilities shared by many tests in this directory
"""
import re
import traceback
from contextlib import contextmanager

from cocotb.triggers import Timer


async def clock_gen(clock):
    """Example clock gen for test use"""
    for i in range(5):
        clock.value = 0
        await Timer(100, "ns")
        clock.value = 1
        await Timer(100, "ns")
    clock._log.warning("Clock generator finished!")


async def _check_traceback(running_coro, exc_type, pattern):
    try:
        await running_coro
    except exc_type:
        tb_text = traceback.format_exc()
    else:
        assert False, "Exception was not raised"

    assert re.match(pattern, tb_text), (
        "Traceback didn't match - got:\n\n"
        "{}\n"
        "which did not match the pattern:\n\n"
        "{}"
    ).format(tb_text, pattern)


@contextmanager
def assert_raises(exc_type, pattern=None):
    try:
        yield
    except exc_type as e:
        if pattern:
            assert re.match(
                pattern, str(e)
            ), "Correct exception type caught, but message did not match pattern"
        pass
    else:
        assert False, f"{exc_type.__name__} was not raised"
