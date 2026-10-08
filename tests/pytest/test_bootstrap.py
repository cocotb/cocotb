# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test native bootstrap failures without a simulator."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from cocotb_tools.config import _shared_library_path, bootstrap_entry


@pytest.mark.parametrize(
    ("entry_point", "expected_message"),
    [
        pytest.param(
            "does_not_exist",
            "Unable to find entry point '{entry_point}' in library '{library}'",
            id="missing_entry_point",
        ),
        pytest.param(
            "gpi_initialize",
            "Entry point '{entry_point}' in library '{library}' failed",
            id="failed_entry_point",
        ),
    ],
)
def test_bootstrap_entry_point_failure(entry_point: str, expected_message: str) -> None:
    library = _shared_library_path("gpi")
    # The bootstrapper calls exit() on failure, so invoke it in a subprocess.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import ctypes\n"
                "import sys\n"
                "bootstrap = ctypes.CDLL(sys.argv[1])\n"
                "bootstrap.cocotb_bootstrap_entry.argtypes = []\n"
                "bootstrap.cocotb_bootstrap_entry.restype = None\n"
                "bootstrap.cocotb_bootstrap_entry()\n"
            ),
            str(_shared_library_path("cocotb_bootstrap")),
        ],
        env={
            **os.environ,
            "COCOTB_BOOTSTRAP": bootstrap_entry(library, entry_point),
            # gpi_initialize returns an error when no implementations are loaded.
            "GPI_IMPL": "",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert (
        expected_message.format(entry_point=entry_point, library=library.as_posix())
        in result.stderr
    )
