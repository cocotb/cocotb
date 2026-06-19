# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from collections.abc import Generator

import pytest

import cocotb.future
from cocotb.future import Future, disable, enable, is_enabled


def none_enabled() -> bool:
    return not cocotb.future._enabled_futures


def all_enabled() -> bool:
    return cocotb.future._enabled_futures == set(Future)


@pytest.fixture(autouse=True)
def clear_futures() -> Generator[None, None, None]:
    """Clear enabled futures before each test."""
    cocotb.future._enabled_futures.clear()
    yield None


def test_futures() -> None:
    # Enable a future and check it is enabled
    assert not is_enabled(Future.PLACEHOLDER)
    enable(Future.PLACEHOLDER)
    assert is_enabled(Future.PLACEHOLDER)

    # Ensure does not raise if enabled multiple times
    enable(Future.PLACEHOLDER)
    assert is_enabled(Future.PLACEHOLDER)


def test_envvar_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COCOTB_FUTURE", raising=False)
    cocotb.future._init()
    assert none_enabled()


def test_envvar_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COCOTB_FUTURE", "")
    cocotb.future._init()
    assert none_enabled()


@pytest.mark.parametrize(
    "true_value",
    [
        "1",
        "true",
        "True",
        "TRUE",
        "on",
        "On",
        "ON",
        "yes",
        "Yes",
        "YES",
        "enable",
        "Enable",
        "ENABLE",
    ],
)
def test_envvar_true(monkeypatch: pytest.MonkeyPatch, true_value: str) -> None:
    monkeypatch.setenv("COCOTB_FUTURE", true_value)
    cocotb.future._init()
    assert all_enabled()


@pytest.mark.parametrize(
    "false_value",
    [
        "0",
        "false",
        "False",
        "FALSE",
        "off",
        "Off",
        "OFF",
        "no",
        "No",
        "NO",
        "disable",
        "Disable",
        "DISABLE",
    ],
)
def test_envvar_false(monkeypatch: pytest.MonkeyPatch, false_value: str) -> None:
    monkeypatch.setenv("COCOTB_FUTURE", false_value)
    cocotb.future._init()
    assert none_enabled()


def test_envvar_by_future(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COCOTB_FUTURE", "placeholder")
    cocotb.future._init()
    assert is_enabled(Future.PLACEHOLDER)
    # Ensure PLACEHOLDER is the only enabled future
    disable(Future.PLACEHOLDER)
    assert not is_enabled(Future.PLACEHOLDER)


def test_envvar_empty_future(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COCOTB_FUTURE", ",placeholder,,")
    cocotb.future._init()
    assert is_enabled(Future.PLACEHOLDER)
    # Ensure it's the only enabled future
    disable(Future.PLACEHOLDER)
    assert not is_enabled(Future.PLACEHOLDER)


def test_envvar_unknown_future(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COCOTB_FUTURE", ",unknown")
    with pytest.raises(ValueError, match=".*'unknown'.*"):
        cocotb.future._init()
    assert none_enabled()
