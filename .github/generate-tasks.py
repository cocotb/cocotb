#!/usr/bin/env python3


tasks = [
    # Test different Python versions with package managed Icarus on Ubuntu
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'apt',
        # lowest version according to https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
        'os': 'ubuntu-20.04', 'python-version': '3.6.7'
    },
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'apt',
        # lowest version according to https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
        'os': 'ubuntu-20.04', 'python-version': '3.7.1'
    },
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'apt',
        'os': 'ubuntu-20.04', 'python-version': '3.8'
    },
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'apt',
        'os': 'ubuntu-20.04', 'python-version': '3.9'
    },
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'apt',
        'os': 'ubuntu-20.04', 'python-version': '3.10'
    },
    # Test Icarus dev on Ubuntu
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'master',
        'os': 'ubuntu-20.04', 'python-version': '3.8'
    },
    # Test GHDL on Ubuntu
    {
        'lang': 'vhdl',
        'sim': 'ghdl', 'sim-version': 'nightly',
        'os': 'ubuntu-latest', 'python-version': '3.8'
    },
    # Test Verilator on Ubuntu
    {
        'lang': 'verilog',
        'sim': 'verilator', 'sim-version': 'master',
        'os': 'ubuntu-20.04', 'python-version': '3.8',
        'may_fail': 'true'
    },
    # Test other OSes
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'homebrew-HEAD',    # Icarus homebrew --HEAD
        'os': 'macos-latest', 'python-version': '3.8'
    },{
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'master',    # Icarus windows master from source
        'os': 'windows-latest', 'python-version': '3.8',
        'toolchain': 'mingw', 'extra_name': 'mingw | '
    },{
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'master',    # use msvc instead of mingw
        'os': 'windows-latest', 'python-version': '3.8',
        'toolchain': 'msvc', 'extra_name': 'msvc | '
    },
    # Other
    {
        'lang': 'verilog',
        'sim': 'icarus', 'sim-version': 'v11_0',    # use clang instead of gcc
        'os': 'ubuntu-20.04', 'python-version': '3.8"',
        'cxx': 'clang++', 'cc': 'clang', 'extra_name': 'clang | '
    }
]

print(f"::set-output name=tasks::{tasks!s}")
