# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Collection of tests that are directly testing pytest plugin
that allows to use pytest as regression manager for cocotb tests.
"""

from __future__ import annotations

from pytest import MonkeyPatch, raises

from cocotb_tools.pytest import env


def test_env_exists(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.pytest.env.exists`."""
    monkeypatch.setenv("TEST_EXISTS", "")
    assert env.exists("TEST_EXISTS")

    monkeypatch.delenv("TEST_EXISTS")
    assert not env.exists("TEST_EXISTS")


def test_env_as_bool(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.pytest.env.as_bool`."""
    monkeypatch.setenv("TEST_BOOL", "")
    assert env.as_bool("TEST_BOOL", True)
    assert not env.as_bool("TEST_BOOL", False)

    for value in ("1", "yes", "y", "ON", "True", "Enable"):
        monkeypatch.setenv("TEST_BOOL", value)
        assert env.as_bool("TEST_BOOL")

    for value in ("0", "no", "n", "OFF", "False", "Disable"):
        monkeypatch.setenv("TEST_BOOL", value)
        assert not env.as_bool("TEST_BOOL")

    for value in ("-1", "2", "l", "x", "y3s", "0N", "Tru3", "3n4b13"):
        with raises(
            ValueError,
            match=f"Unexpected value '{value}' for environment variable: TEST_BOOL\\. Expecting one of .*",
        ):
            monkeypatch.setenv("TEST_BOOL", value)
            env.as_bool("TEST_BOOL", value)
