# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from enum import Enum

import pytest

import cocotb
from cocotb._decorators import _repr, _reprs


class MyEnum(Enum):
    ENUM_VALUE = 1


class A: ...


def b(): ...


def test_parametrize_repr():
    assert _repr(1) == "1"
    assert _repr(False) == "False"
    assert _repr(0.14) == "0.14"
    assert _repr(None) == "None"
    assert _repr("wow") == "wow"
    assert _repr("has space") is None
    assert _repr("😊") is None
    assert _repr("wowthisisareallylongnamethatidontwantonmyterminal") is None
    assert _repr(A) == "A"
    assert _repr(b) == "b"
    assert _repr(MyEnum.ENUM_VALUE) == "ENUM_VALUE"
    assert _repr(object()) is None


def test_parametrize_reprs():
    assert _reprs([1, 0.5, False]) == ["1", "0.5", "False"]
    assert _reprs([9, 9, object()]) == ["0", "1", "2"]


def test_parametrize_bad_args():
    with pytest.raises(ValueError):
        cocotb.parametrize(("not valid", [1, 2, 3], "extra arg whoops"))
    with pytest.raises(ValueError):
        cocotb.parametrize(("not valid", [1, 2, 3]))
    with pytest.raises(ValueError):
        cocotb.parametrize((("not valid", "valid"), [(1, 2), (3, 4)]))
    with pytest.raises(ValueError):
        cocotb.parametrize((("a", "b"), [(1, 2, "too", "many", "args"), (3, 4)]))
