# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Decide which CI tests to run from the GitHub Actions event and local Git history."""

from __future__ import annotations

import json
import os
import subprocess
from fnmatch import fnmatchcase
from pathlib import Path

# Map of reusable workflow output names to which paths should trigger them.
SELECTED_PATHS: dict[str, tuple[str, ...]] = {
    "run_tests": (
        # Project sources
        "src/**",
        "CMakeLists.txt",
        # Project configuration, dependencies and versioning (should visually check outputs for correct version)
        ".codecov.yml",
        "pyproject.toml",
        "VERSION",
        "uv.lock",
        # Any CI changes (easier than keeping track of which workflow files are relevant)
        ".github/**",
        # Any test code changes
        "tests/**",
        "examples/**",
        "noxfile.py",
    ),
    "run_benchmarks": (
        # Project sources
        "src/**",
        "CMakeLists.txt",
        # Project configuration, dependencies and versioning (should visually check outputs for correct version)
        ".codecov.yml",
        "pyproject.toml",
        "VERSION",
        "uv.lock",
        # Benchmark workflow changes
        ".github/workflows/benchmark.yml",
        # Any benchmark code
        "tests/benchmarks/**",
        "examples/matrix_multiplier/**",
    ),
}


def changed_paths(base: str, head: str) -> list[str]:
    """Return a list of paths changed between two git commits."""
    result = subprocess.run(
        ["git", "diff", "--name-only", "--no-renames", "-z", f"{base}...{head}", "--"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]


def tests_to_run(paths: list[str]) -> dict[str, bool]:
    """Given a list of changed paths, return a dictionary of which tests to run."""
    outputs = {}
    for output, selected in SELECTED_PATHS.items():
        outputs[output] = any(
            fnmatchcase(path, pattern) for path in paths for pattern in selected
        )
    return outputs


def main() -> None:
    gh_pr_info = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text())[
        "pull_request"
    ]
    outputs = tests_to_run(
        changed_paths(gh_pr_info["base"]["sha"], gh_pr_info["head"]["sha"])
    )

    # Output all reusable workflow outputs as booleans. Github wants "true" and "false".
    result = "\n".join(
        f"{name}={str(value).lower()}" for name, value in outputs.items()
    )
    with open(os.environ["GITHUB_OUTPUT"], "a") as output_file:
        print(result, file=output_file)

    # Also print to stdout for sanity checking
    print(result)


if __name__ == "__main__":
    main()
