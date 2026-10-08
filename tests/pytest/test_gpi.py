# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test native GPI initialization failures without a simulator."""

from __future__ import annotations

import os
import subprocess
import sys

from cocotb_tools.config import _shared_library_path


def test_gpi_impl_missing_entry_point() -> None:
    library = _shared_library_path("gpi")
    entry_point = "does_not_exist"
    # Use a loadable library so initialization reaches the symbol lookup.
    # GPI calls exit() on failure, so invoke it in a subprocess.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import ctypes\n"
                "import sys\n"
                "gpi = ctypes.CDLL(sys.argv[1])\n"
                "gpi.gpi_initialize.argtypes = []\n"
                "gpi.gpi_initialize.restype = ctypes.c_int\n"
                "gpi.gpi_initialize()\n"
            ),
            str(library),
        ],
        env={
            **os.environ,
            "GPI_IMPL": f"{library.as_posix()}:{entry_point}",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert (
        f"cocotb: Unable to find entry point {entry_point} "
        f"for shared library {library.as_posix()}" in result.stdout
    )
