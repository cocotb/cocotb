#!/usr/bin/env python
"""
Simple script to combine JUnit test results into a single XML file.
"""

import argparse
import os
import re
import sys
from typing import Iterable, Pattern
from xml.etree import ElementTree as ET


def _find_all(name: Pattern, path: str) -> Iterable[str]:
    for root, _, files in os.walk(path):
        for file in files:
            if re.match(name, file):
                yield os.path.join(root, file)


def _get_parser() -> argparse.ArgumentParser:
    """Return the cmdline parser"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["."],
        help="Directories to search for input files.",
    )
    parser.add_argument(
        "-i",
        "--input-filename",
        default="results.xml",
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
                    print(
                        "Testsuite name: {!r}, package: {!r}".format(
                            ts.get("name"), ts.get("package")
                        )
                    )
                for existing in result:
                    if (existing.get("name") == ts.get("name")) and (
                        existing.get("package") == ts.get("package")
                    ):
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

    testsuite_count = 0
    testcase_count = 0
    for testsuite in result.iter("testsuite"):
        testsuite_count += 1
        for testcase in testsuite.iter("testcase"):
            testcase_count += 1
            for failure in testcase.iter("failure"):
                rc = 1
                print(
                    "Failure in testsuite: '{}' classname: '{}' testcase: '{}' with parameters '{}'".format(
                        testsuite.get("name"),
                        testcase.get("classname"),
                        testcase.get("name"),
                        testsuite.get("package"),
                    )
                )
                if os.getenv("GITHUB_ACTIONS") is not None:
                    # Get test file relative to root of repo
                    file = testcase.get("file")
                    assert (
                        file is not None
                    )  # if this file was output by cocotb, it has this attribute
                    repo_root = os.path.commonprefix(
                        [
                            os.path.abspath(file),
                            os.path.abspath(__file__),
                        ]
                    )
                    relative_file = file.replace(repo_root, "")
                    print(
                        "::error file={},line={}::Test {}:{} failed".format(
                            relative_file,
                            testcase.get("lineno"),
                            testcase.get("classname"),
                            testcase.get("name"),
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
