# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import pytest

from cocotb_tools import config


@pytest.mark.parametrize(
    ("interface", "simulator", "entry_function"),
    [
        ("vpi", "cvc", "vlog_startup_routines_bootstrap"),
        ("vpi", "ius", "vlog_startup_routines_bootstrap"),
        ("vpi", "xcelium", "vlog_startup_routines_bootstrap"),
        ("vhpi", "activehdl", "vhpi_startup_routines_bootstrap"),
        ("vhpi", "riviera", "vhpi_startup_routines_bootstrap"),
    ],
)
def test_lib_entry_with_explicit_entry_function(
    interface: str, simulator: str, entry_function: str
) -> None:
    library = config.lib_name_path(interface, simulator).as_posix()

    assert config.lib_entry(interface, simulator) == f"{library}:{entry_function}"


@pytest.mark.parametrize(
    ("interface", "simulator"),
    [
        ("vpi", "icarus"),
        ("vpi", "questa"),
        ("vpi", "vcs"),
        ("vhpi", "ghdl"),
        ("vhpi", "nvc"),
        ("fli", "questa"),
    ],
)
def test_lib_entry_with_standard_entry_function(interface: str, simulator: str) -> None:
    assert (
        config.lib_entry(interface, simulator)
        == config.lib_name_path(interface, simulator).as_posix()
    )


def test_lib_entry_is_case_insensitive() -> None:
    expected_library = config.lib_name_path("vpi", "xcelium").as_posix()

    assert config.lib_entry("VPI", "XCELIUM") == (
        f"{expected_library}:vlog_startup_routines_bootstrap"
    )


def test_lib_name_path_is_case_insensitive() -> None:
    assert config.lib_name_path("VPI", "ICARUS") == config.lib_name_path(
        "vpi", "icarus"
    )
