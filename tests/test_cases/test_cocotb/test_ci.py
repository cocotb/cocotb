# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import os
import sys

import cocotb


@cocotb.test(skip=os.getenv("GITHUB_ACTIONS") is None)
async def test_python_version(_: object) -> None:
    assert sys.version.startswith(os.environ["PYTHON_VERSION"].strip())
