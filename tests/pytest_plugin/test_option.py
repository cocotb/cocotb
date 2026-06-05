# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test :class:`cocotb_tools.pytest._option` module."""

from __future__ import annotations

import os
from collections.abc import Sequence
from unittest import mock

import pytest
from pytest import MonkeyPatch, Pytester, RunResult


@pytest.mark.parametrize(
    "env",
    (
        "COCOTB_REGRESSION_MANAGER",
        "COCOTB_SIM_TIME_UNIT",
        "COCOTB_TOPLEVEL_LANG",
        "COCOTB_SIMULATOR",
        "COCOTB_RESOLVE_X",
        "COCOTB_LOG_LEVEL",
        "GPI_LOG_LEVEL",
    ),
)
def test_option_invalid_choice_from_env(
    pytester: Pytester, monkeypatch: MonkeyPatch, env: str
) -> None:
    """Test invalid option choice when set from environment variable."""
    monkeypatch.setenv(env, "<invalid>")
    result: RunResult = pytester.runpytest()
    assert result.ret


@pytest.mark.parametrize(
    "option,value",
    (
        ("cocotb_trust_inertial_writes", True),
        ("cocotb_trust_inertial_writes", False),
        ("cocotb_waveform_viewer", "surfer"),
        ("cocotb_waveform_viewer", "gtkwave"),
        ("cocotb_scheduler_debug", True),
        ("cocotb_scheduler_debug", False),
        ("cocotb_log_level", None),
        ("cocotb_log_level", "info"),
        ("cocotb_resolve_x", None),
        ("cocotb_resolve_x", "error"),
        ("cocotb_attach", None),
        ("cocotb_attach", 10),
        ("gpi_log_level", None),
        ("gpi_log_level", "info"),
    ),
)
def test_option_envs_set(
    pytester: Pytester,
    monkeypatch: MonkeyPatch,
    option: str,
    value: object,
) -> None:
    """Test options that must be set as environment variables."""
    environment: str = option.upper()
    argument: str = f"--{option.replace('_', '-')}"
    expected: str | None
    args: list[str]

    if not value:
        args = []
        expected = None
    elif value is True:
        args = [argument]
        expected = "1"
    elif isinstance(value, str):
        args = [argument, value]
        expected = value
    elif isinstance(value, Sequence):
        args = [argument] + [str(arg) for arg in value]
        expected = ",".join(value)
    else:
        args = [argument, str(value)]
        expected = str(value)

    pytester.makepyfile(f"""
        import os
        from cocotb_tools.pytest.dut import Dut

        def test_option(dut: Dut) -> None:
            if {expected!r}:
                assert os.environ.get({environment!r}) == {expected!r}
            else:
                assert {environment!r} not in os.environ
    """)

    with mock.patch.dict(os.environ, clear=True):
        if not value:
            # Plugin should unset this environment variable
            monkeypatch.setenv(environment, "")

        result: RunResult = pytester.runpytest(*args)

    result.assert_outcomes(passed=1)
