#!/usr/bin/env python
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys

from setuptools import setup

# Same cap as upstream master; VERSION is the template used by setuptools-git-versioning.
version = open("VERSION").read().strip()
max_python3_minor_version = 14
if "COCOTB_IGNORE_PYTHON_REQUIRES" not in os.environ and sys.version_info >= (
    3,
    max_python3_minor_version + 1,
):
    raise RuntimeError(
        f"cocotb {version} only supports a maximum Python version of 3.{max_python3_minor_version}.\n"
        "You can suppress this error by defining the environment variable COCOTB_IGNORE_PYTHON_REQUIRES\n"
        "There is no guarantee cocotb will work with untested versions of Python and no support will be provided."
    )

# Native libraries: CMake via scikit-build-core. Metadata: pyproject.toml.
setup()
