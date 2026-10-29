# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import warnings
from collections.abc import Generator
from types import SimpleNamespace

import pytest

import cocotb.preview
import cocotb.simulator
from cocotb.handle import (
    EnumObject,
    IntegerObject,
    LogicObject,
    PackedObject,
    RealObject,
)

FEATURE = cocotb.preview.Feature.HANDLE_LEN_IS_SUBELEMENTS


@pytest.fixture(autouse=True)
def isolate_previews() -> Generator[None, None, None]:
    enabled_features = cocotb.preview._enabled_features.copy()
    cocotb.preview._enabled_features.clear()
    yield
    cocotb.preview._enabled_features.clear()
    cocotb.preview._enabled_features.update(enabled_features)


def _packed_array() -> PackedObject:
    """A fake ``logic [7:0][3:0]`` packed array."""
    handle = object.__new__(PackedObject)
    handle._path = "dut.arr"
    handle._handle = SimpleNamespace(
        get_indexable=lambda: 1,
        get_num_elems=lambda: 32,
        get_range=lambda: (7, 0, cocotb.simulator.RANGE_DOWN),
    )
    return handle


def _packed_struct() -> PackedObject:
    """A fake 22-bit packed struct."""
    handle = object.__new__(PackedObject)
    handle._path = "dut.pkt"
    handle._handle = SimpleNamespace(
        get_indexable=lambda: 0,
        get_num_elems=lambda: 22,
    )
    return handle


@pytest.mark.parametrize("enabled", [False, True])
def test_logic_object_len_is_deprecated(enabled: bool) -> None:
    if enabled:
        cocotb.preview.enable(FEATURE)
    handle = object.__new__(LogicObject)

    with pytest.warns(DeprecationWarning):
        assert len(handle) == 1


@pytest.mark.parametrize("enabled", [False, True])
def test_integer_object_len_is_deprecated(enabled: bool) -> None:
    if enabled:
        cocotb.preview.enable(FEATURE)
    handle = object.__new__(IntegerObject)
    handle._handle = SimpleNamespace(get_num_elems=lambda: 8)

    with pytest.warns(DeprecationWarning):
        assert len(handle) == 8


@pytest.mark.parametrize("enabled", [False, True])
def test_enum_object_len_is_deprecated(enabled: bool) -> None:
    if enabled:
        cocotb.preview.enable(FEATURE)
    handle = object.__new__(EnumObject)
    handle._handle = SimpleNamespace(get_num_elems=lambda: 8)

    with pytest.warns(DeprecationWarning):
        assert len(handle) == 8


def test_real_object_len_raises_type_error() -> None:
    handle = object.__new__(RealObject)

    with pytest.raises(TypeError):
        len(handle)


def test_packed_array_len_is_size_without_preview() -> None:
    handle = _packed_array()

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert len(handle) == 32


def test_packed_array_len_is_range_with_preview() -> None:
    cocotb.preview.enable(FEATURE)
    handle = _packed_array()

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert len(handle) == 8
    assert handle.size == 32


def test_packed_struct_len_is_size_without_preview() -> None:
    handle = _packed_struct()

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert len(handle) == 22


def test_packed_struct_len_raises_with_preview() -> None:
    cocotb.preview.enable(FEATURE)
    handle = _packed_struct()

    with pytest.raises(TypeError):
        len(handle)
    assert handle.size == 22
