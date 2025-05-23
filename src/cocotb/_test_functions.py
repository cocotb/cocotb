# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Collection of functions to control a running test and related exceptions."""

from typing import NoReturn, Type, Union

Failed: Type[BaseException]
try:
    import pytest
except ModuleNotFoundError:
    Failed = AssertionError
else:
    try:
        with pytest.raises(Exception):
            pass
    except BaseException as _raises_e:
        Failed = type(_raises_e)
    else:
        assert False, "pytest.raises doesn't raise an exception when it fails"


class TestSuccess(BaseException):
    """Implementation of :func:`pass_test`.

    Users are *not* intended to catch this exception type.
    """

    def __init__(self, msg: Union[str, None]) -> None:
        super().__init__(msg)
        self.msg = msg


def pass_test(msg: Union[str, None] = None) -> NoReturn:
    """Force a test to pass.

    The test will end and enter termination phase when this is called.

    Args:
        msg: The message to display when the test passes.
    """
    raise TestSuccess(msg)
