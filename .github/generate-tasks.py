#!/usr/bin/env python3


tasks = [
  # Test different Python versions with package managed Icarus on Ubuntu
  {
    'sim': 'icarus',
    'sim-version': 'apt',
    'lang': 'verilog',
    # lowest version according to https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
    'python-version': '3.6.7',
    'os': 'ubuntu-20.04'
  },
  {
    'sim': 'icarus',
    'sim-version': 'apt',
    'lang': 'verilog',
    # lowest version according to https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
    'python-version': '3.7.1',
    'os': 'ubuntu-20.04'
  },
  {
    'sim': 'icarus',
    'sim-version': 'apt',
    'lang': 'verilog',
    'python-version': '3.8',
    'os': 'ubuntu-20.04'
  },
  {
    'sim': 'icarus',
    'sim-version': 'apt',
    'lang': 'verilog',
    'python-version': '3.9',
    'os': 'ubuntu-20.04'
  },
  {
    'sim': 'icarus',
    'sim-version': 'apt',
    'lang': 'verilog',
    'python-version': '3.10',
    'os': 'ubuntu-20.04'
  },
  # Test Icarus dev on Ubuntu
  {
    'sim': 'icarus',
    'sim-version': 'master',
    'lang': 'verilog',
    'python-version': '3.8',
    'os': 'ubuntu-20.04',
  },
  # Test GHDL on Ubuntu
  {
    'sim': 'ghdl',
    'sim-version': 'nightly',
    'lang': 'vhdl',
    'python-version': '3.8',
    'os': 'ubuntu-latest',
  },
  # Test Verilator on Ubuntu
  {
    'sim': 'verilator',
    'sim-version': 'master',
    'lang': 'verilog',
    'python-version': '3.8',
    'os': 'ubuntu-20.04',
    'may_fail': 'true',
  },
  # Test other OSes
  {
   'sim': 'icarus',  # Icarus homebrew --HEAD
   'sim-version': 'homebrew-HEAD',
   'lang': 'verilog',
   'python-version': '3.8',
   'os': 'macos-latest',
  },{
    'sim': 'icarus',  # Icarus windows master from source
    'sim-version': 'master',
    'lang': 'verilog',
    'python-version': '3.8',
    'os': 'windows-latest',
    'toolchain': 'mingw',
    'extra_name': 'mingw | ',
  },{
    'sim': 'icarus',  # use msvc instead of mingw
    'sim-version': 'master',
    'lang': 'verilog',
    'python-version': '3.8',
    'os': 'windows-latest',
    'toolchain': 'msvc',
    'extra_name': 'msvc | ',
  },
  # Other
  {
    'sim': 'icarus',  # use clang instead of gcc
    'sim-version': 'v11_0',
    'lang': 'verilog',
    'python-version': '3.8"',
    'os': 'ubuntu-20.04',
    'cxx': 'clang++',
    'cc': 'clang',
    'extra_name': 'clang | ',
  }
]

print(f"::set-output name=tasks::{tasks!s}")
