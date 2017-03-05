#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages
import os

f = open('version', 'r')
version = f.readline()[8:].strip()
f.close()

author = 'Chris Higgs, Stuart Hodgson'
author_email = 'cocotb@potentialventures.com'

install_requires = []

def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths

extra_files = package_files('makefiles')
extra_files += package_files('lib')
extra_files += package_files('include')
extra_files += ['../version']

setup(
    name='cocotb',
    version=version,
    description='**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.',
    url='https://github.com/potentialventures/cocotb',
    license='BSD',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    packages=find_packages(),
    include_package_data=True,
    package_data={'cocotb': extra_files},
    scripts=['bin/cocotb-path'],
    platforms='any'
)
