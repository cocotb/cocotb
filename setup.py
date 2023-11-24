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

if sys.version_info[:2] < (3, 6):
    msg = [
        "This version of cocotb requires at least Python 3.6,",
        "you are running Python %d.%d.%d."
        % (sys.version_info[0], sys.version_info[1], sys.version_info[2]),
    ]
    if sys.version_info[0] == 2:
        msg += [
            "If you have Python 3 installed on your machine try ",
            "using 'python3 -m pip' instead of 'pip' to install cocotb.",
        ]
    msg += [
        "For more information please refer to the documentation at ",
        "https://cocotb.readthedocs.io.",
    ]

    raise SystemExit("\n".join(msg))

import logging
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
    for fpath, _, filenames in walk(directory):
        for filename in filenames:
            paths.append(path.join("..", "..", fpath, filename))
    return paths


# this sets the __version__ variable
exec(read_file(path.join("src", "cocotb", "_version.py")))

# store log from build_libs and display at the end in verbose mode
# see https://github.com/pypa/pip/issues/6634
log_stream = StringIO()
handler = logging.StreamHandler(log_stream)
log = logging.getLogger("cocotb._build_libs")
log.setLevel(logging.INFO)
log.addHandler(handler)

setup(
    cmdclass={"build_ext": build_ext},
    version=__version__,  # noqa: F821
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
    platforms="any",
)

print(log_stream.getvalue())
