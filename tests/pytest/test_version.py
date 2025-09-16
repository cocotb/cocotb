# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import shutil
import subprocess

import cocotb


def test_version():
    if "dev" in cocotb.__version__ and os.path.exists(".git") and shutil.which("git"):
        assert "+" in cocotb.__version__
        parts = cocotb.__version__.split("+")
        rev = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], universal_newlines=True
        ).strip()
        assert parts[1] == rev, (
            "Installed cocotb version is not the same as your latest git version"
        )
