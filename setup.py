#!/usr/bin/env python
# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import os
import sys
from io import StringIO
from os import path, walk

from setuptools import find_packages, setup

# Note: cocotb is not installed properly yet and is missing dependencies and binaries
# We can still import other files next to setup.py, as long as they're in MANIFEST.in
# The below line is necessary for PEP517 support
sys.path.append(path.dirname(__file__))

from cocotb_build_libs import build_ext, get_ext

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


def package_files(directory):
    paths = []
    for fpath, _, filenames in walk(directory):
        for filename in filenames:
            paths.append(path.join("..", "..", fpath, filename))
    return paths


# store log from build_libs and display at the end in verbose mode
# see https://github.com/pypa/pip/issues/6634
log_stream = StringIO()
handler = logging.StreamHandler(log_stream)
log = logging.getLogger("cocotb_build_libs")
log.setLevel(logging.INFO)
log.addHandler(handler)

setup(
    cmdclass={"build_ext": build_ext},
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "cocotb": (
            package_files("src/cocotb/share/include")
            + package_files("src/cocotb/share/def")
            + package_files("src/cocotb/share/lib/verilator")
        ),
        "cocotb_tools": (package_files("src/cocotb_tools/makefiles")),
    },
    ext_modules=get_ext(),
)

print(log_stream.getvalue())
