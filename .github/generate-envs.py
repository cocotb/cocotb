#!/usr/bin/env python3
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Get a list test environments."""

import argparse
import json
import sys

ENVS = [
    # Test different Python versions with package managed Icarus on Ubuntu
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        # lowest version according to https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
        "os": "ubuntu-20.04",
        "python-version": "3.6.7",
        "group": "ci",
    },
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        # lowest version according to https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json
        "os": "ubuntu-20.04",
        "python-version": "3.7.1",
        "group": "ci",
    },
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        "os": "ubuntu-20.04",
        "python-version": "3.9",
        "group": "ci",
    },
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        "os": "ubuntu-20.04",
        "python-version": "3.10",
        "group": "ci",
    },
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        "os": "ubuntu-20.04",
        "python-version": "3.11",
        "group": "ci",
    },
    # A single test for the upcoming Python version.
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        "os": "ubuntu-20.04",
        "python-version": "3.12.0-alpha - 3.12.0",
        "group": "experimental",
    },
    # Test Icarus on Ubuntu
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "master",
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        "group": "experimental",
    },
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "v11_0",  # The latest release version.
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        "group": "experimental",
    },
    # Test GHDL on Ubuntu
    {
        "lang": "vhdl",
        "sim": "ghdl",
        "sim-version": "v2.0.0",  # GHDL 2.0 is the minimum supported version.
        "os": "ubuntu-latest",
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "vhdl",
        "sim": "ghdl",
        "sim-version": "master",
        "os": "ubuntu-latest",
        "python-version": "3.8",
        "group": "experimental",
    },
    # Test Verilator on Ubuntu
    {
        "lang": "verilog",
        "sim": "verilator",
        "sim-version": "v4.106",
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        # Various cocotb tests are known to fail with Verilator 4.106.
        # Newer versions of Verilator are not working at all.
        # See also https://github.com/cocotb/cocotb/issues/2300
        "group": "experimental",
    },
    {
        "lang": "verilog",
        "sim": "verilator",
        "sim-version": "master",
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        # Tests are currently not expected to work at all.
        # See also https://github.com/cocotb/cocotb/issues/2300
        "group": "experimental",
    },
    # Test other OSes
    # Icarus homebrew
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "homebrew-stable",
        "os": "macos-11",
        "python-version": "3.8",
        "group": "ci",
    },
    # Icarus homebrew (HEAD/master)
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "homebrew-HEAD",
        "os": "macos-11",
        "python-version": "3.8",
        "group": "experimental",
    },
    # Icarus windows from source
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "b83daa3ae36891a372655652e53c9b4eefdfcafa",
        "os": "windows-latest",
        "python-version": "3.8",
        "toolchain": "mingw",
        "extra_name": "mingw | ",
        # mingw tests fail silently currently due to test harness limitations.
        "group": "experimental",
    },
    # use msvc instead of mingw
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "b83daa3ae36891a372655652e53c9b4eefdfcafa",
        "os": "windows-latest",
        "python-version": "3.8",
        "toolchain": "msvc",
        "extra_name": "msvc | ",
        "group": "ci",
    },
    # Other
    # use clang instead of gcc
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "b83daa3ae36891a372655652e53c9b4eefdfcafa",
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        "cxx": "clang++",
        "cc": "clang",
        "extra_name": "clang | ",
        "group": "ci",
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group")
    parser.add_argument("--output-format", choices=("gha", "json"), default="json")

    args = parser.parse_args()

    if args.group is not None and args.group != "":
        selected_envs = [t for t in ENVS if "group" in t and t["group"] == args.group]
    else:
        # Return all tasks if no group is selected.
        selected_envs = ENVS

    if args.output_format == "gha":
        # Output for GitHub Actions (GHA). Sets the variable 'envs'.

        # The generated JSON output may not contain newlines to be parsed by GHA
        print(f"::set-output name=envs::{json.dumps(selected_envs)}")

        # The set-output command is not visible in the GHA logs; print the
        # the selected environments for easier debugging.
        print("Generated the following test configurations:")
        print(json.dumps(selected_envs, indent=2))
    elif args.output_format == "json":
        print(json.dumps(selected_envs, indent=2))
    else:
        assert False

    return 0


if __name__ == "__main__":
    sys.exit(main())
