# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from types import SimpleNamespace

import pytest

from cocotb.handle import (
    EnumObject,
    IntegerObject,
    LogicObject,
    RealObject,
)


def test_logic_object_len_is_deprecated() -> None:
    handle = object.__new__(LogicObject)

    assert handle.size == 1
    with pytest.warns(DeprecationWarning):
        assert len(handle) == 1


def test_integer_object_len_is_deprecated() -> None:
    handle = object.__new__(IntegerObject)
    handle._handle = SimpleNamespace(get_num_elems=lambda: 8)

    assert handle.size == 8
    with pytest.warns(DeprecationWarning):
        assert len(handle) == 8


def test_enum_object_len_is_deprecated() -> None:
    handle = object.__new__(EnumObject)
    handle._handle = SimpleNamespace(get_num_elems=lambda: 8)

    assert handle.size == 8
    with pytest.warns(DeprecationWarning):
        assert len(handle) == 8


def test_real_object_len_raises_type_error() -> None:
    handle = object.__new__(RealObject)

    with pytest.raises(TypeError):
        len(handle)
