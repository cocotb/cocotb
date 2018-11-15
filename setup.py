#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages
from os import path, walk

here = path.abspath(path.dirname(__file__))

with open(path.join(here,'version'), 'r') as f:
    version = f.readline()[8:].strip()

with open(path.join(here, 'README.md'), 'r') as f:
    long_description = f.read()

author = 'Chris Higgs, Stuart Hodgson'
author_email = 'cocotb@potentialventures.com'

install_requires = []

def package_files(directory):
    paths = []
    for (fpath, directories, filenames) in walk(directory):
        for filename in filenames:
            paths.append(path.join('..', fpath, filename))
    return paths

extra_files = package_files('makefiles')
extra_files += package_files('lib')
extra_files += package_files('include')

setup(
    name='cocotb',
    version=version,
    description='**cocotb** is a coroutine based cosimulation library for writing VHDL and Verilog testbenches in Python.',
    url='https://github.com/potentialventures/cocotb',
    license='BSD',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    packages=find_packages(),
    include_package_data=True,
    package_data={'cocotb': extra_files},
    entry_points={
        'console_scripts': [
            'cocotb-path=cocotb.path:main',
        ]
    },
    platforms='any'
)

