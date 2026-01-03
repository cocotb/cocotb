# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Testing the :py:mod:`cocotb_tools.env` module used to handle
environment variables in consistent and friendly way."""

from __future__ import annotations

import shlex
from pathlib import Path
from re import escape

from pytest import MonkeyPatch, raises

from cocotb_tools import env


def test_env_exists_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.exists` with existing environment variable."""
    monkeypatch.setenv("TEST_EXISTS", "")
    assert env.exists("TEST_EXISTS")


def test_env_exists_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.exists` with undefined environment variable."""
    monkeypatch.delenv("TEST_EXISTS", raising=False)
    assert not env.exists("TEST_EXISTS")


def test_env_bool_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_bool` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_BOOL", "")
    assert not env.as_bool("TEST_BOOL")


def test_env_bool_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_bool` when environment variable is undefined."""
    monkeypatch.delenv("TEST_BOOL", raising=False)
    assert not env.as_bool("TEST_BOOL")


def test_env_bool_default(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_bool` with default value."""
    monkeypatch.delenv("TEST_BOOL", raising=False)
    assert env.as_bool("TEST_BOOL", True)
    assert not env.as_bool("TEST_BOOL", False)


def test_env_bool_true(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_bool` with environment variable set to true."""
    for value in ("1", "yes", "y", "ON", "True", "Enable"):
        monkeypatch.setenv("TEST_BOOL", value)
        assert env.as_bool("TEST_BOOL")


def test_env_bool_false(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_bool` with environment variable set to false."""
    for value in ("0", "no", "n", "OFF", "False", "Disable"):
        monkeypatch.setenv("TEST_BOOL", value)
        assert not env.as_bool("TEST_BOOL")


def test_env_bool_invalid(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_bool` with environment variable set to invalid value."""
    for value in ("-1", "2", "l", "x", "y3s", "0N", "Tru3", "3n4b13"):
        with raises(
            ValueError,
            match=escape(
                f"Unexpected value '{value}' for environment variable: 'TEST_BOOL'. Expecting one of "
                "('1', 'yes', 'y', 'on', 'true', 'enable') or ('0', 'no', 'n', 'off', 'false', 'disable')"
            ),
        ):
            monkeypatch.setenv("TEST_BOOL", value)
            env.as_bool("TEST_BOOL")


def test_env_path_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_path` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_PATH", "")
    assert env.as_path("TEST_PATH") == Path(".").resolve()


def test_env_path_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_path` when environment variable is undefined."""
    monkeypatch.delenv("TEST_PATH", raising=False)
    assert env.as_path("TEST_PATH") == Path(".").resolve()


def test_env_path_default(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test :py:func:`cocotb_tools.env.as_path` with default value."""
    monkeypatch.delenv("TEST_PATH", raising=False)
    assert env.as_path("TEST_PATH", tmp_path) == tmp_path.resolve()


def test_env_path_set(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test :py:func:`cocotb_tools.env.as_path` with environment variable set to path."""
    monkeypatch.setenv("TEST_PATH", str(tmp_path))
    assert env.as_path("TEST_PATH") == tmp_path.resolve()
    assert env.as_path("TEST_PATH", "default") == tmp_path.resolve()


def test_env_paths_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_paths` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_PATHS", "")
    assert env.as_paths("TEST_PATHS") == []


def test_env_paths_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_paths` when environment variable is undefined."""
    monkeypatch.delenv("TEST_PATHS", raising=False)
    assert env.as_paths("TEST_PATHS") == []


def test_env_paths_default(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test :py:func:`cocotb_tools.env.as_paths` with default value."""
    monkeypatch.delenv("TEST_PATHS", raising=False)
    assert env.as_paths("TEST_PATHS", tmp_path) == [tmp_path]


def test_env_paths_set(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test :py:func:`cocotb_tools.env.as_paths` with environment variable set to path."""
    path1: Path = tmp_path / "a"
    path2: Path = tmp_path / "b"
    path3: Path = tmp_path / "c"

    monkeypatch.setenv("TEST_PATHS", f"{path1}")
    assert env.as_paths("TEST_PATHS") == [path1]
    assert env.as_paths("TEST_PATHS", "default") == [path1]

    monkeypatch.setenv("TEST_PATHS", f"  {path1},{path2},,  {path3} ,, ")
    assert env.as_paths("TEST_PATHS") == [path1, path2, path3]
    assert env.as_paths("TEST_PATHS", "default") == [path1, path2, path3]


def test_env_str_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_str` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_STRING", "")
    assert env.as_str("TEST_STRING") == ""


def test_env_str_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_str` when environment variable is undefined."""
    monkeypatch.delenv("TEST_STRING", raising=False)
    assert env.as_str("TEST_STRING") == ""


def test_env_str_default(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_str` with default value."""
    monkeypatch.delenv("TEST_STRING", raising=False)
    assert env.as_str("TEST_STRING", "default") == "default"


def test_env_str_set(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_str` with environment variable set to string."""
    monkeypatch.setenv("TEST_STRING", "  value ")
    assert env.as_str("TEST_STRING") == "value"


def test_env_int_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_int` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_INT", "")
    assert env.as_int("TEST_INT") == 0


def test_env_int_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_int` when environment variable is undefined."""
    monkeypatch.delenv("TEST_INT", raising=False)
    assert env.as_int("TEST_INT") == 0


def test_env_int_default(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_int` with default value."""
    monkeypatch.delenv("TEST_INT", raising=False)

    for value in (-13, -1, 0, 1, 20):
        assert env.as_int("TEST_INT", value) == value


def test_env_int_set(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_int` with environment variable set to integer."""
    for value in (-13, -1, 0, 1, 20):
        monkeypatch.setenv("TEST_INT", str(value))
        assert env.as_int("TEST_INT") == value


def test_env_args_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_args` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_ARGS", "")
    assert env.as_args("TEST_ARGS") == []


def test_env_args_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_args` when environment variable is undefined."""
    monkeypatch.delenv("TEST_ARGS", raising=False)
    assert env.as_args("TEST_ARGS") == []


def test_env_args_default(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_args` with default value."""
    expected: str = "arg1 arg2 'arg3 arg4' arg5"
    monkeypatch.delenv("TEST_ARGS", raising=False)
    assert env.as_args("TEST_ARGS", expected) == shlex.split(expected)


def test_env_args_set(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_args` with environment variable set to arguments."""
    expected: str = "arg1 arg2 'arg3 arg4' arg5"
    monkeypatch.setenv("TEST_ARGS", expected)
    assert env.as_args("TEST_ARGS", "default") == shlex.split(expected)


def test_env_list_empty(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_list` when environment variable is defined but empty."""
    monkeypatch.setenv("TEST_LIST", "")
    assert env.as_list("TEST_LIST") == []


def test_env_list_undefined(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_list` when environment variable is undefined."""
    monkeypatch.delenv("TEST_LIST", raising=False)
    assert env.as_list("TEST_LIST") == []


def test_env_list_default(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_list` with default value."""
    monkeypatch.delenv("TEST_LIST", raising=False)
    assert env.as_list("TEST_LIST", ["a", "b", "c", "d"]) == ["a", "b", "c", "d"]


def test_env_list_set(monkeypatch: MonkeyPatch) -> None:
    """Test :py:func:`cocotb_tools.env.as_list` with environment variable set to arguments."""
    monkeypatch.setenv("TEST_LIST", " a,  b ,c,,d ,")
    assert env.as_list("TEST_LIST", "default") == ["a", "b", "c", "d"]
