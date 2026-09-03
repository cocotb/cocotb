# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from collections.abc import Generator

import pytest

import cocotb.preview
from cocotb.handle import (
    EnumObject,
    IntegerObject,
    LogicObject,
    RealObject,
)


@pytest.fixture(autouse=True)
def enable_handle_len_preview() -> Generator[None, None, None]:
    enabled_features = cocotb.preview._enabled_features.copy()
    cocotb.preview._enabled_features.clear()
    cocotb.preview.enable(cocotb.preview.Feature.HANDLE_LEN)
    assert cocotb.preview.is_enabled(cocotb.preview.Feature.HANDLE_LEN)
    yield
    cocotb.preview._enabled_features.clear()
    cocotb.preview._enabled_features.update(enabled_features)


def test_logic_object_len_raises_type_error() -> None:
    handle = object.__new__(LogicObject)

    with pytest.raises(TypeError):
        len(handle)


def test_integer_object_len_raises_type_error() -> None:
    handle = object.__new__(IntegerObject)

    with pytest.raises(TypeError):
        len(handle)


def test_enum_object_len_raises_type_error() -> None:
    handle = object.__new__(EnumObject)

    with pytest.raises(TypeError):
        len(handle)


def test_real_object_len_raises_type_error() -> None:
    handle = object.__new__(RealObject)

    with pytest.raises(TypeError):
        len(handle)
