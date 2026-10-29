# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Run the Makefile-based regression suites and examples."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from cocotb_tools import combine_results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "group",
        nargs="?",
        choices=("all", "tests", "examples"),
        default="all",
        help="Suites to run (default: all).",
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop after the first failed suite."
    )
    parser.add_argument(
        "--clean", action="store_true", help="Run make clean in each suite."
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    env = os.environ.copy()
    env.setdefault("SIM", "icarus")
    env.setdefault("TOPLEVEL_LANG", "verilog")

    suites: list[Path] = []
    if args.group in ("all", "tests"):
        suites.extend(
            makefile.parent
            for makefile in sorted((repo_root / "tests/test_cases").glob("*/Makefile"))
        )
    if args.group in ("all", "examples"):
        examples = [
            "adder/tests",
            "simple_dff",
            "matrix_multiplier/tests",
            "mixed_language/tests",
        ]
        if env["TOPLEVEL_LANG"] == "verilog":
            if env["SIM"] not in ("ius", "xcelium"):
                print("Skipping example mixed_signal since only Xcelium is supported")
            elif shutil.which("spectre") is None:
                print("Skipping example mixed_signal since Spectre is not available")
            else:
                examples.append("mixed_signal/tests")
            examples.append("first_steps")
        suites.extend(repo_root / "examples" / example for example in examples)

    failed = 0
    completed = 0
    for suite in suites:
        name = suite.relative_to(repo_root).as_posix()
        command = ["make"]
        if not args.fail_fast:
            command.append("-k")
        if args.clean:
            command.append("clean")
        elif repo_root / "examples" in suite.parents:
            # Examples may set these unconditionally in their Makefiles.
            command.extend(
                (f"SIM={env['SIM']}", f"TOPLEVEL_LANG={env['TOPLEVEL_LANG']}")
            )

        print(
            f"Running {'clean for' if args.clean else 'regression suite'} {name}",
            flush=True,
        )
        result = subprocess.run(
            command, cwd=suite, env={**env, "PWD": str(suite)}, check=False
        )
        completed += 1
        if result.returncode:
            failed += 1
            message = f"Failed regression suite {name} (make exited with status {result.returncode})"
            if os.environ.get("GITHUB_ACTIONS") == "true":
                message = "::error::" + message.replace("%", "%25").replace(
                    "\r", "%0D"
                ).replace("\n", "%0A")
            print(message, flush=True)
            if args.fail_fast:
                break

    print(f"Ran {completed} suites: {failed} failed.", flush=True)
    rc = int(failed != 0)
    if not args.clean:
        combined_rc = combine_results.main(
            [
                str(repo_root),
                "--repo-root",
                str(repo_root),
                "--output-file",
                str(repo_root / "combined_results.xml"),
            ]
        )
        rc = rc or combined_rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
