# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Common utilities shared by many tests in this directory
"""
import re
import traceback


async def _check_traceback(running_coro, exc_type, pattern, *match_args):
    try:
        await running_coro
    except exc_type:
        tb_text = traceback.format_exc()
    else:
        assert False, "Exception was not raised"

    assert re.match(pattern, tb_text, *match_args), (
        "Traceback didn't match - got:\n\n"
        "{}\n"
        "which did not match the pattern:\n\n"
        "{}"
    ).format(tb_text, pattern)


class MyException(Exception):
    ...


class MyBaseException(BaseException):
    ...
