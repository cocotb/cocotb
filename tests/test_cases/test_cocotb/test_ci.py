# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys

import cocotb


@cocotb.skipif(os.getenv("GITHUB_ACTIONS") is None)
@cocotb.test
async def test_python_version(_: object) -> None:
    assert sys.version.startswith(os.environ["PYTHON_VERSION"].strip())
