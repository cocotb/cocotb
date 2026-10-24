# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import warnings
from types import SimpleNamespace
from typing import Any

import pytest

import cocotb.handle
from cocotb.handle import RealObject


def _real_object(monkeypatch: pytest.MonkeyPatch) -> tuple[RealObject, list[Any]]:
    """A fake ``real`` object that records the values written to it."""
    monkeypatch.setattr(cocotb.handle, "current_gpi_trigger", lambda: None)
    handle = object.__new__(RealObject)
    handle._handle = SimpleNamespace(
        get_const=lambda: False,
        get_signal_val_real=lambda: 1.5,
    )
    written: list[Any] = []
    handle._set_value = lambda value, action: written.append(value)
    return handle, written


def test_get_is_deprecated(monkeypatch: pytest.MonkeyPatch) -> None:
    handle, _ = _real_object(monkeypatch)

    with pytest.deprecated_call():
        assert handle.get() == 1.5


def test_set_is_deprecated(monkeypatch: pytest.MonkeyPatch) -> None:
    handle, written = _real_object(monkeypatch)

    with pytest.deprecated_call():
        handle.set(2.5)
    assert written == [2.5]


def test_value_is_not_deprecated(monkeypatch: pytest.MonkeyPatch) -> None:
    handle, written = _real_object(monkeypatch)

    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert handle.value == 1.5
        handle.value = 2.5
    assert written == [2.5]
