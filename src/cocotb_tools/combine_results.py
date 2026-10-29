# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""
Simple script to combine JUnit test results into a single XML file.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from re import Pattern
from xml.etree import ElementTree as ET

log = logging.getLogger(__name__)

_DEFAULT_INPUT_FILENAME = r"(results.*|.*\.result)\.xml"


@dataclass
class Results:
    """Collected suites, test cases, and counts for callers to report or write."""

    testsuite_count: int = 0
    testcase_count: int = 0
    testsuites: list[ET.Element] = field(default_factory=list)
    testcases: list[tuple[str | None, ET.Element]] = field(default_factory=list)
    failed_testcases: list[tuple[str | None, ET.Element]] = field(default_factory=list)


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
        default=_DEFAULT_INPUT_FILENAME,
        help="A regular expression to match input filenames.",
    )
    parser.add_argument(
        "-o",
        "--output-file",
        type=Path,
        default=Path("combined_results.xml"),
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


def combine_results(
    directories: Iterable[Path], input_filename: str = _DEFAULT_INPUT_FILENAME
) -> Results:
    """Collect and merge XML results from *directories* that match *input_filename*."""
    results = Results()

    input_pattern = re.compile(input_filename)

    for directory in directories:
        log.debug("Searching in %s for results XML files.", directory)
        for fname in _find_all(input_pattern, directory):
            log.debug("Reading file %s.", fname)
            tree = ET.parse(fname)
            for ts in tree.iter("testsuite"):
                log.debug("Testsuite name: %r", ts.get("name"))
                for existing in results.testsuites:
                    if existing.get("name") == ts.get("name"):
                        log.debug(
                            "Testsuite already exists in combined results. Extending it."
                        )
                        existing.extend(list(ts))
                        break
                else:
                    log.debug(
                        "Testsuite does not already exist in combined results. Adding it."
                    )
                    results.testsuites.append(ts)

    results.testsuite_count = len(results.testsuites)
    for testsuite in results.testsuites:
        for testcase in testsuite.iter("testcase"):
            test_result = (testsuite.get("name"), testcase)
            results.testcases.append(test_result)
            if (
                testcase.find("failure") is not None
                or testcase.find("error") is not None
            ):
                results.failed_testcases.append(test_result)
    results.testcase_count = len(results.testcases)
    return results


def main(argv: Sequence[str] | None = None) -> int:
    parser = _get_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    results = combine_results(args.directories, input_filename=args.input_filename)
    workspace = args.repo_root.resolve() if args.repo_root else Path.cwd()

    for testsuite_name, testcase in results.failed_testcases:
        properties = _get_properties(testcase)
        file = properties.get("file")
        if file is not None and (file_path := Path(file)).is_absolute():
            try:
                file = str(file_path.resolve().relative_to(workspace))
            except ValueError:
                pass

        print(
            "Failure in testsuite: '{}' testcase: '{}.{}' file: '{}::{}'".format(
                testsuite_name,
                testcase.get("classname"),
                testcase.get("name"),
                file,
                properties.get("line"),
            )
        )

    print(
        f"Ran a total of {results.testsuite_count} TestSuites and {results.testcase_count} TestCases"
    )
    log.debug("Writing combined results to %s", args.output_file)
    root = ET.Element("testsuites", name=args.output_testsuites_name)
    root.extend(results.testsuites)
    ET.ElementTree(root).write(args.output_file, encoding="UTF-8")
    return int(len(results.failed_testcases) != 0)


if __name__ == "__main__":
    sys.exit(main())
