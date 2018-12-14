#!/usr/bin/env python

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
)

