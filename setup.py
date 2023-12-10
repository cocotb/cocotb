#!/usr/bin/env python
###############################################################################
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

import sys

if sys.version_info[:2] < (3, 6):  # noqa: UP036 | bug in ruff
    msg = [
        "This version of cocotb requires at least Python 3.6,",
        "you are running Python %d.%d.%d."
        % (sys.version_info[0], sys.version_info[1], sys.version_info[2]),
    ]
    msg += [
        "For more information please refer to the documentation at ",
        "https://cocotb.readthedocs.io.",
    ]

    raise SystemExit("\n".join(msg))

import logging
import subprocess
from io import StringIO
from os import path, walk

from setuptools import find_packages, setup

# Note: cocotb is not installed properly yet and is missing dependencies and binaries
# We can still import other files next to setup.py, as long as they're in MANIFEST.in
# The below line is necessary for PEP517 support
sys.path.append(path.dirname(__file__))
from cocotb_build_libs import build_ext, get_ext  # noqa: E402


def read_file(fname):
    with open(path.join(path.dirname(__file__), fname), encoding="utf8") as f:
        return f.read()


def package_files(directory):
    paths = []
    for fpath, directories, filenames in walk(directory):
        for filename in filenames:
            paths.append(path.join("..", "..", fpath, filename))
    return paths


version_file_path = path.join("src", "cocotb", "_version.py")
__version__ = "2.0.0.dev0"
if "dev" in __version__:
    try:
        rev = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], universal_newlines=True
        ).strip()
        __version__ += f"+{rev}"
    except Exception as e:
        # if this is not a git repository and _version.py already exists,
        # we are probably installing from an sdist, so use the existing _version.py
        if path.exists(version_file_path):
            exec(read_file(version_file_path))
        else:
            print(e, file=sys.stderr)
with open(version_file_path, "w") as f:
    f.write("# Package version\n")
    f.write("# Generated by setup.py -- do not modify directly\n\n")
    f.write(f'__version__ = "{__version__}"')


# store log from build_libs and display at the end in verbose mode
# see https://github.com/pypa/pip/issues/6634
log_stream = StringIO()
handler = logging.StreamHandler(log_stream)
log = logging.getLogger("cocotb._build_libs")
log.setLevel(logging.INFO)
log.addHandler(handler)

setup(
    name="cocotb",
    cmdclass={"build_ext": build_ext},
    version=__version__,
    description="cocotb is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.",
    url="https://www.cocotb.org",
    license="BSD",
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    author="Chris Higgs, Stuart Hodgson",
    maintainer="cocotb contributors",
    maintainer_email="cocotb@lists.librecores.org",
    install_requires=[
        "find_libpython",
    ],
    python_requires=">=3.6",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    package_data={
        "cocotb": (
            package_files("src/cocotb/share/makefiles")
            + package_files("src/cocotb/share/include")  # noqa: W504
            + package_files("src/cocotb/share/def")  # noqa: W504
            + package_files("src/cocotb/share/lib/verilator")  # noqa: W504
        )
    },
    ext_modules=get_ext(),
    entry_points={
        "console_scripts": [
            "cocotb-config=cocotb.config:main",
        ]
    },
    platforms="any",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: BSD License",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Framework :: cocotb",
    ],
    # these appear in the sidebar on PyPI
    project_urls={
        "Bug Tracker": "https://github.com/cocotb/cocotb/issues",
        "Source Code": "https://github.com/cocotb/cocotb",
        "Documentation": "https://docs.cocotb.org",
    },
)

print(log_stream.getvalue())
