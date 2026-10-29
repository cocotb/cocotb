# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import subprocess
import sys

import pytest

from cocotb_tools.config import libs_dir


@pytest.mark.skipif(
    sys.platform != "linux",
    reason="SONAME is Linux-specific shared library metadata",
)
def test_libgpi_has_soname() -> None:
    libgpi = libs_dir / "libgpi.so"
    output = subprocess.check_output(
        ["readelf", "-d", libgpi],
        text=True,
    )

    assert "Library soname: [libgpi.so]" in output
