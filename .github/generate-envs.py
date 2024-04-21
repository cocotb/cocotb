#!/usr/bin/env python3
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Generate a list of test environments.

Each environment must contain the following fields:
- lang: The TOPLEVEL_LANG of the test. Must be one of "verilog" or "vhdl".
- sim: The SIM of the test. Must be one of "icarus", "ghdl", "nvc", "verilator", "riviera", "questa", or "xcelium".
- sim-version: The version of the simulator to use. Valid values depend upon the simulator and build recipe.
- os: The OS to operate on. Must be a valid value for the "jobs.<job_name>.runs-on" field for Github Actions.
- python-version: The Python version to test with. Must be a valid value for the "python-version" field of the "actions/setup-python" Github Action.
- group: The group to run the test in. One of "ci", "experimental", or "extended". See below note.

Optional fields:
- self-hosted: True if test needs to be run on a self-hosted Github Action runner. Default: False.
- cc: C compiler and linker to use. Default: gcc.
- cxx: C++ compiler and linker to use. Default: g++.
- extra_name: Additional tag prepended to computed name for test. Default: <none>.

What tests belong in what groups:
- ci: The most recent stable release of a given simulator, all supported versions of Python, and all supported operating systems. Run on all PRs and master pushes.
- experimental: Development HEAD for each simulator, any under-development version of Python, and under-development simulator. Run weekly.
- extended: The minimum supoprted version of a simulator, and a smattering of released simulator versions between the minimum and most recent. Run weekly.

Ideally, whenever a new version of a simulator is released, a new test should be added for that simulator.
The current test in the "ci" group should be moved to "extended",
and the new version should be added to "ci" and any changes in behavior recorded with expectations to make CI pass.
"""

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
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        "os": "ubuntu-20.04",
        "python-version": "3.12",
        "group": "ci",
    },
    # A single test for the upcoming Python version.
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "apt",
        "os": "ubuntu-20.04",
        "python-version": "3.13.0-alpha - 3.13.0",
        "group": "experimental",
    },
    # Test Icarus on Ubuntu
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "v12_0",  # The latest release version.
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "master",
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
        "group": "extended",
    },
    {
        "lang": "vhdl",
        "sim": "ghdl",
        "sim-version": "v3.0.0",
        "os": "ubuntu-latest",
        "python-version": "3.8",
        "group": "extended",
    },
    {
        "lang": "vhdl",
        "sim": "ghdl",
        "sim-version": "v4.1.0",  # The latest release version.
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
    # Test NVC on Ubuntu
    {
        "lang": "vhdl",
        "sim": "nvc",
        "sim-version": "r1.11.3",  # The latest release version.
        "os": "ubuntu-latest",
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "vhdl",
        "sim": "nvc",
        "sim-version": "master",
        "os": "ubuntu-latest",
        "python-version": "3.8",
        "group": "experimental",
    },
    # Test Verilator on Ubuntu
    {
        "lang": "verilog",
        "sim": "verilator",
        "sim-version": "v5.024",  # Latest release version.
        # Needs 22.04 for newer GCC with C++ coroutine support used with --timing mode
        "os": "ubuntu-22.04",
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "verilog",
        "sim": "verilator",
        "sim-version": "master",
        # Needs 22.04 for newer GCC with C++ coroutine support used with --timing mode
        "os": "ubuntu-22.04",
        "python-version": "3.8",
        "group": "experimental",
    },
    {
        "lang": "verilog",
        "sim": "verilator",
        "sim-version": "v5.022",  # Minimum supported version.
        # Needs 22.04 for newer GCC with C++ coroutine support used with --timing mode
        "os": "ubuntu-22.04",
        "python-version": "3.8",
        "group": "extended",
    },
    # Test other OSes
    # Icarus homebrew
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "homebrew-stable",
        "os": "macos-12",
        "python-version": "3.8",
        "group": "ci",
    },
    # Icarus homebrew (HEAD/master)
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "homebrew-HEAD",
        "os": "macos-12",
        "python-version": "3.8",
        "group": "experimental",
    },
    # Verilator macOS
    {
        "lang": "verilog",
        "sim": "verilator",
        "sim-version": "stable",
        "os": "macos-13",
        "python-version": "3.8",
        "group": "ci",
    },
    # Icarus windows from source
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "v12_0",
        "os": "windows-latest",
        "python-version": "3.11",
        "toolchain": "mingw",
        "extra-name": "mingw",
        "group": "ci",
    },
    # use msvc instead of mingw
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "v12_0",
        "os": "windows-latest",
        "python-version": "3.11",
        "toolchain": "msvc",
        "extra-name": "msvc",
        "group": "ci",
    },
    # Other
    # use clang instead of gcc
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "v12_0",
        "os": "ubuntu-20.04",
        "python-version": "3.8",
        "cxx": "clang++",
        "cc": "clang",
        "extra-name": "clang",
        "group": "ci",
    },
    # Test Siemens Questa on Ubuntu
    {
        "lang": "verilog",
        "sim": "questa",
        "sim-version": "siemens/questa/2023.4",
        "os": "ubuntu-20.04",
        "self-hosted": True,
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "vhdl and fli",
        "sim": "questa",
        "sim-version": "siemens/questa/2023.4",
        "os": "ubuntu-20.04",
        "self-hosted": True,
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "vhdl and vhpi",
        "sim": "questa",
        "sim-version": "siemens/questa/2023.4",
        "os": "ubuntu-20.04",
        "self-hosted": True,
        "python-version": "3.8",
        "group": "ci",
    },
    # Test Aldec Riviera-PRO on Ubuntu
    {
        "lang": "verilog",
        "sim": "riviera",
        "sim-version": "aldec/rivierapro/2023.10",
        "os": "ubuntu-20.04",
        "self-hosted": True,
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "vhdl",
        "sim": "riviera",
        "sim-version": "aldec/rivierapro/2023.10",
        "os": "ubuntu-20.04",
        "self-hosted": True,
        "python-version": "3.8",
        "group": "ci",
    },
    # Test Cadence Xcelium on Ubuntu
    {
        "lang": "verilog",
        "sim": "xcelium",
        "sim-version": "cadence/xcelium/2309",
        "os": "ubuntu-20.04",
        "self-hosted": True,
        "python-version": "3.8",
        "group": "ci",
    },
    {
        "lang": "vhdl",
        "sim": "xcelium",
        "sim-version": "cadence/xcelium/2309",
        "os": "ubuntu-20.04",
        "self-hosted": True,
        "python-version": "3.8",
        "group": "ci",
    },
]

# Questa: test more versions as part of the extended tests.
questa_versions_novhpi = ("2021.2", "2021.3", "2021.4", "2022.1", "2022.2")
questa_versions_vhpi = ("2022.3", "2022.4", "2023.1", "2023.2")

for version in questa_versions_novhpi + questa_versions_vhpi:
    ENVS += [
        {
            "lang": "verilog",
            "sim": "questa",
            "sim-version": f"siemens/questa/{version}",
            "os": "ubuntu-20.04",
            "self-hosted": True,
            "python-version": "3.8",
            "group": "extended",
        },
        {
            "lang": "vhdl and fli",
            "sim": "questa",
            "sim-version": f"siemens/questa/{version}",
            "os": "ubuntu-20.04",
            "self-hosted": True,
            "python-version": "3.8",
            "group": "extended",
        },
    ]
for version in questa_versions_vhpi:
    ENVS += [
        {
            "lang": "vhdl and vhpi",
            "sim": "questa",
            "sim-version": f"siemens/questa/{version}",
            "os": "ubuntu-20.04",
            "self-hosted": True,
            "python-version": "3.8",
            "group": "extended",
        },
    ]

# Riviera-PRO: test more versions as part of the extended tests.
riviera_versions = ("2019.10", "2020.04", "2020.10", "2021.04", "2021.10", "2022.04")
for version in riviera_versions:
    ENVS += [
        {
            "lang": "verilog",
            "sim": "riviera",
            "sim-version": f"aldec/rivierapro/{version}",
            "os": "ubuntu-20.04",
            "self-hosted": True,
            "python-version": "3.8",
            "group": "extended",
        },
        {
            "lang": "vhdl",
            "sim": "riviera",
            "sim-version": f"aldec/rivierapro/{version}",
            "os": "ubuntu-20.04",
            "self-hosted": True,
            "python-version": "3.8",
            "group": "extended",
        },
    ]


def append_str_val(listref, my_list, key) -> None:
    if key not in my_list:
        return
    listref.append(str(my_list[key]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group")
    parser.add_argument("--output-format", choices=("gha", "json"), default="json")
    parser.add_argument(
        "--gha-output-file",
        type=argparse.FileType("a", encoding="utf-8"),
        help="The $GITHUB_OUTPUT file.",
    )

    args = parser.parse_args()

    if args.group is not None and args.group != "":
        selected_envs = [t for t in ENVS if "group" in t and t["group"] == args.group]
    else:
        # Return all tasks if no group is selected.
        selected_envs = ENVS

    for env in selected_envs:
        # The "runs-on" job attribute is a string if we're using the GitHub-
        # provided hosted runners, or an array with special keys if we're
        # using self-hosted runners.
        if "self-hosted" in env and env["self-hosted"] and "runs-on" not in env:
            env["runs-on"] = ["self-hosted", f"cocotb-private-{env['os']}"]
        else:
            env["runs-on"] = env["os"]

        # Assemble the human-readable name of the job.
        name_parts = []
        append_str_val(name_parts, env, "extra-name")
        append_str_val(name_parts, env, "sim")
        if "/" in env["sim-version"]:
            # Shorten versions like 'siemens/questa/2023.2' to '2023.2'.
            name_parts.append(env["sim-version"].split("/")[-1])
        else:
            name_parts.append(env["sim-version"])
        append_str_val(name_parts, env, "lang")
        append_str_val(name_parts, env, "os")
        append_str_val(name_parts, env, "python-version")
        if "may-fail" in env and env["may-fail"]:
            name_parts.append("May fail")

        env["name"] = "|".join(name_parts)

    if args.output_format == "gha":
        # Output for GitHub Actions (GHA). Appends the configuration to
        # the file named in the "--gha-output-file" argument.

        assert args.gha_output_file is not None

        # The generated JSON output may not contain newlines to be parsed by GHA
        print(f"envs={json.dumps(selected_envs)}", file=args.gha_output_file)

        # Print the the selected environments for easier debugging.
        print("Generated the following test configurations:")
        print(json.dumps(selected_envs, indent=2))
    elif args.output_format == "json":
        print(json.dumps(selected_envs, indent=2))
    else:
        assert False

    return 0


if __name__ == "__main__":
    sys.exit(main())
