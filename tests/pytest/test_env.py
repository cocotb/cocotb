# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Testing the :mod:`cocotb_tools.env` module used to handle
environment variables in a consistent and unified way."""

from __future__ import annotations

import shlex
from importlib import reload
from logging import getLogger
from pathlib import Path
from re import escape
from typing import Callable

import pytest
from pytest import MonkeyPatch, raises

import cocotb
import cocotb._init
import cocotb._profiling
import cocotb.types._resolve
from cocotb.handle import SimHandleBase
from cocotb_tools import _env


@cocotb.test
async def dummy(dut: SimHandleBase) -> None:
    """Dummy cocotb test used to test some functions from :mod:`cocotb` package."""


def test_env_exists_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.exists` with existing environment variable."""
    monkeypatch.setenv("TEST_EXISTS", "")
    assert _env.exists("TEST_EXISTS")


def test_env_exists_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.exists` with undefined environment variable."""
    monkeypatch.delenv("TEST_EXISTS", raising=False)
    assert not _env.exists("TEST_EXISTS")


def test_env_bool_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_bool` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_BOOL", "")
    assert not _env.as_bool("TEST_BOOL")


def test_env_bool_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_bool` when environment variable is undefined."""
    monkeypatch.delenv("TEST_BOOL", raising=False)
    assert not _env.as_bool("TEST_BOOL")


def test_env_bool_default(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_bool` with default value."""
    monkeypatch.delenv("TEST_BOOL", raising=False)
    assert _env.as_bool("TEST_BOOL", True)
    assert not _env.as_bool("TEST_BOOL", False)


def test_env_bool_true(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_bool` with environment variable set to true."""
    for value in ("1", "yes", "y", "ON", "True", "Enable"):
        monkeypatch.setenv("TEST_BOOL", value)
        assert _env.as_bool("TEST_BOOL")


def test_env_bool_false(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_bool` with environment variable set to false."""
    for value in ("0", "no", "n", "OFF", "False", "Disable"):
        monkeypatch.setenv("TEST_BOOL", value)
        assert not _env.as_bool("TEST_BOOL")


def test_env_bool_invalid(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_bool` with environment variable set to invalid value."""
    for value in ("-1", "2", "l", "x", "y3s", "0N", "Tru3", "3n4b13"):
        with raises(
            ValueError,
            match=escape(
                f"Unexpected value '{value}' for environment variable: 'TEST_BOOL'. Expecting one of "
                "('1', 'yes', 'y', 'on', 'true', 'enable') or ('0', 'no', 'n', 'off', 'false', 'disable')"
            ),
        ):
            monkeypatch.setenv("TEST_BOOL", value)
            _env.as_bool("TEST_BOOL")


def test_env_path_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_path` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_PATH", "")
    assert _env.as_path("TEST_PATH") == Path(".").resolve()


def test_env_path_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_path` when environment variable is undefined."""
    monkeypatch.delenv("TEST_PATH", raising=False)
    assert _env.as_path("TEST_PATH") == Path(".").resolve()


def test_env_path_default(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test :func:`cocotb_tools._env.as_path` with default value."""
    monkeypatch.delenv("TEST_PATH", raising=False)
    assert _env.as_path("TEST_PATH", tmp_path) == tmp_path.resolve()


def test_env_path_set(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test :func:`cocotb_tools._env.as_path` with environment variable set to path."""
    monkeypatch.setenv("TEST_PATH", str(tmp_path))
    assert _env.as_path("TEST_PATH") == tmp_path.resolve()
    assert _env.as_path("TEST_PATH", "default") == tmp_path.resolve()


def test_env_str_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_str` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_STRING", "")
    assert _env.as_str("TEST_STRING") == ""


def test_env_str_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_str` when environment variable is undefined."""
    monkeypatch.delenv("TEST_STRING", raising=False)
    assert _env.as_str("TEST_STRING") == ""


def test_env_str_default(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_str` with default value."""
    monkeypatch.delenv("TEST_STRING", raising=False)
    assert _env.as_str("TEST_STRING", "default") == "default"


def test_env_str_set(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_str` with environment variable set to string."""
    monkeypatch.setenv("TEST_STRING", "  value ")
    assert _env.as_str("TEST_STRING") == "value"


def test_env_int_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_int` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_INT", "")
    assert _env.as_int("TEST_INT") == 0


def test_env_int_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_int` when environment variable is undefined."""
    monkeypatch.delenv("TEST_INT", raising=False)
    assert _env.as_int("TEST_INT") == 0


def test_env_int_default(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_int` with default value."""
    monkeypatch.delenv("TEST_INT", raising=False)

    for value in (-13, -1, 0, 1, 20):
        assert _env.as_int("TEST_INT", value) == value


def test_env_int_set(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_int` with environment variable set to integer."""
    for value in (-13, -1, 0, 1, 20):
        monkeypatch.setenv("TEST_INT", str(value))
        assert _env.as_int("TEST_INT") == value


def test_env_args_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_args` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_ARGS", "")
    assert _env.as_args("TEST_ARGS") == []


def test_env_args_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_args` when environment variable is undefined."""
    monkeypatch.delenv("TEST_ARGS", raising=False)
    assert _env.as_args("TEST_ARGS") == []


def test_env_args_default(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_args` with default value."""
    expected: str = "arg1 arg2 'arg3 arg4' arg5"
    monkeypatch.delenv("TEST_ARGS", raising=False)
    assert _env.as_args("TEST_ARGS", expected) == shlex.split(expected)


def test_env_args_set(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_args` with environment variable set to arguments."""
    expected: str = "arg1 arg2 'arg3 arg4' arg5"
    monkeypatch.setenv("TEST_ARGS", expected)
    assert _env.as_args("TEST_ARGS", "default") == shlex.split(expected)


def test_env_list_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_list` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_LIST", "")
    assert _env.as_list("TEST_LIST") == []


def test_env_list_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_list` when environment variable is undefined."""
    monkeypatch.delenv("TEST_LIST", raising=False)
    assert _env.as_list("TEST_LIST") == []


def test_env_list_default(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_list` with default value."""
    monkeypatch.delenv("TEST_LIST", raising=False)
    assert _env.as_list("TEST_LIST", ["a", "b", "c", "d"]) == ["a", "b", "c", "d"]


def test_env_list_set(monkeypatch: MonkeyPatch) -> None:
    """Test :func:`cocotb_tools._env.as_list` with environment variable set to arguments."""
    monkeypatch.setenv("TEST_LIST", " a,  b ,c,,d ,")
    assert _env.as_list("TEST_LIST", "default") == ["a", "b", "c", "d"]


def test_env_cocotb_testcase_deprecated(monkeypatch: MonkeyPatch) -> None:
    """Test if defining :envvar:`COCOTB_TESTCASE` environment variable will raise a deprecation warning."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.setenv("COCOTB_TEST_MODULES", "test_env")
    monkeypatch.delenv("COCOTB_TEST_FILTER", raising=False)
    monkeypatch.setenv("COCOTB_TESTCASE", "dummy")

    with pytest.deprecated_call():
        cocotb._init._setup_regression_manager()


def test_env_cocotb_test_modules_empty(monkeypatch: MonkeyPatch) -> None:
    """Test if empty :envvar:`COCOTB_TEST_MODULES` environment variable will raise a runtime error."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.setenv("COCOTB_TEST_MODULES", "")

    with pytest.raises(
        RuntimeError,
        match=escape(
            "Environment variable COCOTB_TEST_MODULES, which defines the module(s) to execute, is not defined or empty."
        ),
    ):
        cocotb._init._setup_regression_manager()


def test_env_cocotb_test_modules_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test if undefined :envvar:`COCOTB_TEST_MODULES` environment variable will raise a runtime error."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.delenv("COCOTB_TEST_MODULES", raising=False)

    with pytest.raises(
        RuntimeError,
        match=escape(
            "Environment variable COCOTB_TEST_MODULES, which defines the module(s) to execute, is not defined or empty."
        ),
    ):
        cocotb._init._setup_regression_manager()


def test_env_cocotb_testcase_with_cocotb_test_filter(monkeypatch: MonkeyPatch) -> None:
    """Test if defined :envvar:`COCOTB_TESTCASE` with :envvar:`COCOTB_TEST_FILETER` environment variable will raise a runtime error."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.setenv("COCOTB_TEST_MODULES", "test_env")
    monkeypatch.setenv("COCOTB_TEST_FILTER", "dummy")
    monkeypatch.setenv("COCOTB_TESTCASE", "dummy")

    with pytest.raises(
        RuntimeError,
        match="Specify only one of COCOTB_TESTCASE or COCOTB_TEST_FILTER",
    ):
        cocotb._init._setup_regression_manager()


def test_env_cocotb_random_seed(monkeypatch: MonkeyPatch) -> None:
    """Test setting :envvar:`COCOTB_RANDOM_SEED` environment variable."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.setattr(cocotb._init, "log", getLogger("cocotb"), raising=False)
    monkeypatch.setenv("COCOTB_RANDOM_SEED", "100")

    cocotb._init._setup_random_seed()

    assert cocotb.RANDOM_SEED == 100


def test_env_random_seed_deprecated(monkeypatch: MonkeyPatch) -> None:
    """Test if defining :envvar:`RANDOM_SEED` environment variable will raise a deprecation warning."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.setattr(cocotb._init, "log", getLogger("cocotb"), raising=False)
    monkeypatch.delenv("COCOTB_RANDOM_SEED", raising=False)
    monkeypatch.setenv("RANDOM_SEED", "110")

    with pytest.deprecated_call():
        cocotb._init._setup_random_seed()
        assert cocotb.RANDOM_SEED == 110


def test_plusargs_ntb_random_seed_deprecated(monkeypatch: MonkeyPatch) -> None:
    """Test if setting plusargs ``ntb_random_seed`` will raise a deprecation warning."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.setattr(cocotb._init, "log", getLogger("cocotb"), raising=False)
    monkeypatch.delenv("COCOTB_RANDOM_SEED", raising=False)
    monkeypatch.delenv("RANDOM_SEED", raising=False)
    monkeypatch.setattr(cocotb, "plusargs", {"ntb_random_seed": "120"}, raising=False)

    with pytest.deprecated_call():
        cocotb._init._setup_random_seed()
        assert cocotb.RANDOM_SEED == 120


def test_plusargs_seed_deprecated(monkeypatch: MonkeyPatch) -> None:
    """Test if setting plusargs ``seed`` will raise a deprecation warning."""
    monkeypatch.setattr(cocotb, "RANDOM_SEED", 0, raising=False)
    monkeypatch.setattr(cocotb._init, "log", getLogger("cocotb"), raising=False)
    monkeypatch.delenv("COCOTB_RANDOM_SEED", raising=False)
    monkeypatch.delenv("RANDOM_SEED", raising=False)
    monkeypatch.setattr(cocotb, "plusargs", {"seed": "130"}, raising=False)

    with pytest.deprecated_call():
        cocotb._init._setup_random_seed()
        assert cocotb.RANDOM_SEED == 130


def test_env_cocotb_enable_profiling(monkeypatch: MonkeyPatch) -> None:
    """Test setting :envvar:`COCOTB_ENABLE_PROFILING` environment variable."""
    for value in ("yes", "no"):
        monkeypatch.setenv("COCOTB_ENABLE_PROFILING", value)
        reload(cocotb._profiling)

        cocotb._profiling.initialize()

        with cocotb._profiling.profiling_context:
            pass

        cocotb._profiling.finalize()


def test_env_cocotb_resolve_x_weak(monkeypatch: MonkeyPatch) -> None:
    """Test setting :envvar:`COCOTB_RESOLVE_X` environment variable to ``weak`` value."""
    monkeypatch.setenv("COCOTB_RESOLVE_X", "weak")

    resolve: Callable[[str], str] | None = cocotb.types._resolve._init()

    assert resolve
    assert resolve("0") == "0"
    assert resolve("1") == "1"
    assert resolve("L") == "0"
    assert resolve("H") == "1"
    assert resolve("W") == "X"


def test_env_cocotb_resolve_x_value_error(monkeypatch: MonkeyPatch) -> None:
    """Test setting :envvar:`COCOTB_RESOLVE_X` environment variable to deprecated ``value_error``."""
    monkeypatch.setenv("COCOTB_RESOLVE_X", "value_error")

    resolve: Callable[[str], str] | None = cocotb.types._resolve._init()

    assert resolve
    assert resolve("0") == "0"
    assert resolve("1") == "1"


def test_env_cocotb_resolve_x_invalid(monkeypatch: MonkeyPatch) -> None:
    """Test setting :envvar:`COCOTB_RESOLVE_X` environment variable to invalid value."""
    monkeypatch.setenv("COCOTB_RESOLVE_X", "invalid")

    with pytest.raises(
        ValueError,
        match=escape(
            "Invalid COCOTB_RESOLVE_X value: 'invalid'. Valid values are 'error', 'weak', 'zeros', 'ones', or 'random'"
        ),
    ):
        cocotb.types._resolve._init()
