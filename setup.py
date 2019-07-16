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

from setuptools import setup
from setuptools import find_packages
from os import path, walk

def read_file(fname):
    return open(path.join(path.dirname(__file__), fname)).read()

def package_files(directory):
    paths = []
    for (fpath, directories, filenames) in walk(directory):
        for filename in filenames:
            paths.append(path.join('..', fpath, filename))
    return paths

version = read_file('version')[8:].strip()

setup(
    name='cocotb',
    version=version,
    description='cocotb is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.',
    url='https://github.com/potentialventures/cocotb',
    license='BSD',
    long_description=read_file('README.md'),
    long_description_content_type='text/markdown',
    author='Chris Higgs, Stuart Hodgson',
    author_email='cocotb@potentialventures.com',
    install_requires=[],
    packages=find_packages(),
    include_package_data=True,
    package_data={'cocotb': package_files('cocotb/share')},
    entry_points={
        'console_scripts': [
            'cocotb-config=cocotb.config:main',
        ]
    },
    platforms='any',
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
)
