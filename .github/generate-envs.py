#!/usr/bin/env python3
# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Generate a list of test environments.

Each environment must contain the following fields:
- lang: The TOPLEVEL_LANG of the test. Must be one of "verilog" or "vhdl".
- sim: The SIM of the test. Must be one of "icarus", "ghdl", "nvc", "verilator", "riviera", "questa", "xcelium", or "vcs".
- sim-version: The version of the simulator to use. Valid values depend upon the simulator and build recipe.
- os: The OS to operate on. Must be a valid value for the "jobs.<job_name>.runs-on" field for Github Actions.
- python-version: The Python version to test with. Must be a valid value for the "python-version" field of the "actions/setup-python" Github Action.
- group: The group to run the test in. One of "ci-free", "ci-licensed", "experimental", or "extended". See below note.

Optional fields:
- self-hosted: True if test needs to be run on a self-hosted Github Action runner. Default: False.
- cc: C compiler and linker to use. Default: gcc.
- cxx: C++ compiler and linker to use. Default: g++.
- extra_name: Additional tag prepended to computed name for test. Default: <none>.
- test_nosim: Runs tests that do not require a simulator in addition to tests that do. Default: False.

What tests belong in what groups:
- ci-free: The most recent stable release of a given free simulator, all supported versions of Python, and all supported operating systems. Run on all PRs and master pushes.
- ci-licensed: The most recent stable release of a given licensed simulator. Run on all PRs and master pushes in the cocotb repo, but are skipped in forks.
- experimental: Development HEAD for each simulator, any under-development version of Python, and under-development simulator. Run weekly.
- extended: The minimum supoprted version of a simulator, and a smattering of released simulator versions between the minimum and most recent. Run weekly.

Ideally, whenever a new version of a simulator is released, a new test should be added for that simulator.
The current test in the "ci-free"/"ci-licensed" group should be moved to "extended",
and the new version should be added to "ci-free"/"ci-licensed" and any changes in behavior recorded with expectations to make CI pass.
"""

import argparse
import json
import sys

ENVS = [
    # NVC windows
    {
        "lang": "vhdl",
        "sim": "nvc",
        "sim-version": "r1.17.1",
        "os": "windows-latest",
        "python-version": "3.11",
        "group": "ci-free",
        "test_nosim": True,
    },
    # Icarus windows from source
    {
        "lang": "verilog",
        "sim": "icarus",
        "sim-version": "v12_0",
        "os": "windows-latest",
        "python-version": "3.11",
        "group": "ci-free",
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
        if env.get("may-fail") is not None:
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
