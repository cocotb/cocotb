# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Checks if a JUnit results file exists and whether there was failing tests."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.etree import ElementTree


def get_results(results_xml_file: Path) -> tuple[int, int]:
    """Return number of tests and fails in *results_xml_file*.

    Returns:
        Tuple of number of tests and number of fails.

    Raises:
        RuntimeError: If *results_xml_file* is non-existent.
    """

    __tracebackhide__ = True  # Hide the traceback when using PyTest.

    if not results_xml_file.is_file():
        raise RuntimeError(
            f"ERROR: Simulation terminated abnormally. Results file {results_xml_file} not found."
        )

    # pytest --junit-xml=<file> is generating proper JUnit XML report file
    # It is using errors attribute as indicator for failed tests without execution but
    # also as indicator for failed pytest (invalid arguments, configuration, setup, ...)
    num_tests = 0
    num_failed = 0  # Failed tests during execution (including setup and call)
    num_errors = 0  # Errors in pytest configuration, fixtures, setup, tests

    tree = ElementTree.parse(results_xml_file)
    for ts in tree.iter("testsuite"):
        if "tests" in ts.attrib:  # pytest, compatible with JUnit XML specification
            num_tests += int(ts.attrib.get("tests", 0))
            num_failed += int(ts.attrib.get("failures", 0))
            num_errors += int(ts.attrib.get("errors", 0))

        else:  # cocotb, non-compatible with Junit XML specification
            # TODO: Remove that when XUnitReporter will be aligned with XUnit schema
            for tc in ts.iter("testcase"):
                num_tests += 1
                for _ in tc.iter("failure"):
                    num_failed += 1

    return (num_tests, num_failed + num_errors)


def _get_parser() -> argparse.ArgumentParser:
    """Return the cmdline parser"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results_file", help="Path to XML file holding JUnit test results.", type=Path
    )
    return parser


def main() -> int:
    parser = _get_parser()
    args = parser.parse_args()

    try:
        (_, num_failed) = get_results(args.results_file)
    except RuntimeError:
        return 1
    return num_failed


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
