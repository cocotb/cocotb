# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
#!/usr/bin/env python
"""
Simple script to combine JUnit test results into a single XML file.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable
from pathlib import Path
from re import Pattern
from xml.etree import ElementTree as ET


def _find_all(name: Pattern, path: Path) -> Iterable[Path]:
    for obj in path.iterdir():
        if obj.is_file() and re.match(name, obj.name):
            yield obj
        elif obj.is_dir():
            yield from _find_all(name, obj)


def _existing_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Path '{path_str}' does not exist.")
    return path


def _get_properties(element: ET.Element) -> dict[str, str]:
    return {
        item.get("name", ""): item.get("value", "") for item in element.iter("property")
    }


def _get_parser() -> argparse.ArgumentParser:
    """Return the cmdline parser"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "directories",
        nargs="*",
        type=_existing_path,
        default=[Path()],
        help="Directories to search for input files.",
    )
    parser.add_argument(
        "-i",
        "--input-filename",
        default=r"results.*\.xml",
        help="A regular expression to match input filenames.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        default="combined_results.xml",
        help="Path of output XML file.",
    )
    parser.add_argument(
        "--output-testsuites-name",
        default="results",
        help="Name of 'testsuites' element in output XML file.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enables verbose output.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        help="Specify root of cocotb repo the regression is run from (CI only).",
    )
    return parser


def main() -> int:
    parser = _get_parser()
    args = parser.parse_args()
    rc = 0

    result = ET.Element("testsuites", name=args.output_testsuites_name)

    input_pattern = re.compile(args.input_filename)

    for directory in args.directories:
        if args.verbose:
            print(f"Searching in {directory} for results.xml files.")
        for fname in _find_all(input_pattern, directory):
            if args.verbose:
                print(f"Reading file {fname}.")
            tree = ET.parse(fname)
            for ts in tree.iter("testsuite"):
                if args.verbose:
                    print("Testsuite name: {!r}".format(ts.get("name")))
                for existing in result:
                    if existing.get("name") == ts.get("name"):
                        if args.verbose:
                            print(
                                "Testsuite already exists in combined results. Extending it."
                            )
                        existing.extend(list(ts))
                        break
                else:
                    if args.verbose:
                        print(
                            "Testsuite does not already exist in combined results. Adding it."
                        )
                    result.append(ts)

    workspace: Path = Path(args.repo_root).resolve() if args.repo_root else Path.cwd()

    testsuite_count: int = 0
    testcase_count: int = 0

    for testsuite in result.findall("testsuite"):
        testsuite_count += 1

        for testcase in testsuite.iter("testcase"):
            testcase_count += 1

            if testcase.find("failure") is None and testcase.find("error") is None:
                continue

            properties: dict[str, str] = _get_properties(testcase)
            file: Path | str | None = properties.get("file")
            rc = 1

            if file and Path(file).is_absolute():
                try:
                    file = Path(file).resolve().relative_to(workspace)
                except ValueError:
                    pass

            print(
                "Failure in testsuite: '{}' testcase: '{}.{}' file: '{}::{}'".format(
                    testsuite.get("name"),
                    testcase.get("classname"),
                    testcase.get("name"),
                    file,
                    properties.get("line"),
                )
            )

    print(f"Ran a total of {testsuite_count} TestSuites and {testcase_count} TestCases")

    if args.verbose:
        print(f"Writing combined results to {args.output_file}")
    ET.ElementTree(result).write(args.output_file, encoding="UTF-8")
    return rc


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
