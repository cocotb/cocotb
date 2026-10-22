# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from collections.abc import Generator

import pytest

import cocotb_previews
from cocotb_previews import Feature, disable, enable, is_enabled


def none_enabled() -> bool:
    return not cocotb_previews._enabled_features


def all_enabled() -> bool:
    return cocotb_previews._enabled_features == set(Feature)


@pytest.fixture(autouse=True)
def clear_features() -> Generator[None, None, None]:
    """Clear enabled preview features before each test."""
    cocotb_previews._enabled_features.clear()
    yield None


def test_features() -> None:
    # Enable a preview feature and check it is enabled.
    assert not is_enabled(Feature.XFAIL_IN_RESULTS)
    enable(Feature.XFAIL_IN_RESULTS)
    assert is_enabled(Feature.XFAIL_IN_RESULTS)

    # Ensure does not raise if enabled multiple times
    enable(Feature.XFAIL_IN_RESULTS)
    assert is_enabled(Feature.XFAIL_IN_RESULTS)


def test_envvar_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COCOTB_PREVIEW", raising=False)
    cocotb_previews._init()
    assert none_enabled()


def test_envvar_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COCOTB_PREVIEW", "")
    cocotb_previews._init()
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
    monkeypatch.setenv("COCOTB_PREVIEW", true_value)
    cocotb_previews._init()
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
    monkeypatch.setenv("COCOTB_PREVIEW", false_value)
    cocotb_previews._init()
    assert none_enabled()


@pytest.mark.parametrize("feature", list(Feature))
def test_envvar_by_feature(monkeypatch: pytest.MonkeyPatch, feature: Feature) -> None:
    monkeypatch.setenv("COCOTB_PREVIEW", feature.value)
    cocotb_previews._init()
    assert is_enabled(feature)
    # Ensure this is the only enabled feature.
    disable(feature)
    assert none_enabled()


def test_envvar_empty_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COCOTB_PREVIEW", ",xfail_in_results,,")
    cocotb_previews._init()
    assert is_enabled(Feature.XFAIL_IN_RESULTS)
    # Ensure it's the only enabled feature.
    disable(Feature.XFAIL_IN_RESULTS)
    assert not is_enabled(Feature.XFAIL_IN_RESULTS)


def test_envvar_unknown_feature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COCOTB_PREVIEW", ",unknown")
    with pytest.raises(ValueError, match=".*'unknown'.*"):
        cocotb_previews._init()
    assert none_enabled()


def test_deprecated_cocotb_preview() -> None:
    import cocotb.preview  # noqa: PLC0415

    with pytest.deprecated_call():
        assert cocotb.preview.Feature is Feature

    with pytest.deprecated_call():
        from cocotb.preview import enable as deprecated_enable  # noqa: PLC0415
    assert deprecated_enable is enable

    with pytest.deprecated_call():
        cocotb.preview._enabled_features = {Feature.XFAIL_IN_RESULTS}
    assert cocotb_previews._enabled_features == {Feature.XFAIL_IN_RESULTS}
    cocotb_previews._enabled_features = set()

    with pytest.raises(AttributeError):
        _ = cocotb.preview.does_not_exist
