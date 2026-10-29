# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys

import pytest

import cocotb

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


@cocotb.test
async def test_xfail(_: object) -> None:
    pytest.xfail("This test is expected to fail")


class MyException(Exception):
    pass


@cocotb.test(expect_fail=True)
async def test_expect_arg_assert(_: object) -> None:
    assert False


@cocotb.test(expect_fail=True)
async def test_expect_arg_raises(_: object) -> None:
    with pytest.raises(ValueError):
        pass


@cocotb.test(expect_fail=True)
async def test_expect_arg_warns(_: object) -> None:
    with pytest.warns(DeprecationWarning):
        pass


@cocotb.test(expect_error=MyException)
async def test_expect_arg_exception(_: object) -> None:
    raise MyException()


@cocotb.test
@cocotb.xfail(reason="This test is expected to fail")
async def test_xfail_assert(_: object) -> None:
    assert False


@cocotb.test
@cocotb.xfail(reason="This test is expected to fail")
async def test_xfail_raises(_: object) -> None:
    with pytest.raises(ValueError):
        pass


@cocotb.test
@cocotb.xfail(reason="This test is expected to fail")
async def test_xfail_warns(_: object) -> None:
    with pytest.warns(DeprecationWarning):
        pass


@cocotb.test
@cocotb.xfail(raises=MyException, reason="This test is expected to fail")
async def test_xfail_exception(_: object) -> None:
    raise MyException()


@cocotb.test
@cocotb.xfail(
    raises=pytest.RaisesGroup(
        ValueError,
        ValueError,
        pytest.RaisesExc(TypeError, match="^expected int$"),
        match="^my group$",
    )
)
async def test_xfail_with_raises_group(dut: object) -> None:
    raise ExceptionGroup(
        "my group",
        [
            ValueError(),
            TypeError("expected int"),
            ValueError(),
        ],
    )


@cocotb.test
@cocotb.xfail(raises=pytest.RaisesGroup(pytest.RaisesGroup(ValueError)))
async def test_xfail_with_raises_group_nested(dut: object) -> None:
    raise ExceptionGroup("", (ExceptionGroup("", (ValueError(),)),))
