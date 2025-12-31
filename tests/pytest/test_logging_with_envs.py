# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Testing the :mod:`cocotb.logging` module."""

from __future__ import annotations

import re
from logging import INFO, getLogger
from random import randint

import pytest
from pytest import LogCaptureFixture, MonkeyPatch

import cocotb.logging
import cocotb.simulator

# X.XX{step,fs,ps,ns,us,ms,sec} <LEVEL> <name> (<file>.py:<line> in <function>)? <message>
LOG: re.Pattern[str] = re.compile(
    r"^\s*[0-9]+\.[0-9]{2}[a-z]{1,4}\s+[A-Z]+\s+\w+\s+(\S+\.py:[0-9]+\s+in\s+\w+)?\s+\w+.*$"
)

BOOLEAN_ENVS: tuple[str, ...] = (
    "COCOTB_REDUCED_LOG_FMT",
    "COCOTB_ANSI_OUTPUT",
    "NO_COLOR",
    "GUI",
)

ENVS: tuple[str, ...] = (
    "COCOTB_LOG_PREFIX",
    *BOOLEAN_ENVS,
)


def mock_get_sim_time() -> tuple[int, int]:
    """Mock the :func:`cocotb.simulator.get_sim_time` function."""
    return 0, int(randint(0, 1000) * 1e4)


def _set_env(monkeypatch: MonkeyPatch, name: str, value: str | None) -> None:
    """Set environment variable."""
    for env in ENVS:
        monkeypatch.delenv(env, raising=False)

    if value is None:
        monkeypatch.delenv(name, raising=False)
    else:
        monkeypatch.setenv(name, value)

    monkeypatch.setattr(
        cocotb.simulator, "get_sim_time", mock_get_sim_time, raising=False
    )

    cocotb.logging._init()
    cocotb.logging._configure()


@pytest.mark.parametrize("value", (None, "0", "1"))
@pytest.mark.parametrize("name", BOOLEAN_ENVS)
def test_logging_boolean_envs(
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
    name: str,
    value: str | None,
) -> None:
    """Test logging module with different boolean environment variables."""
    _set_env(monkeypatch, name, value)

    with caplog.at_level(INFO):
        caplog.clear()
        getLogger("cocotb").warning("warning message")
        assert LOG.match(caplog.text)


@pytest.mark.parametrize("value", (None, "", "prefix"))
def test_logging_log_prefix(
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
    value: str | None,
) -> None:
    """Test logging module with the :envvar:`COCOTB_LOG_PREFIX` environment variable."""
    _set_env(monkeypatch, "COCOTB_LOG_PREFIX", value)

    with caplog.at_level(INFO):
        getLogger("cocotb").info("test message")

        if value:
            assert caplog.text.rstrip() == f"{value}test message"
        else:
            assert LOG.match(caplog.text)
