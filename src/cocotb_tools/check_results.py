# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
"""Checks if a JUnit results file exists and whether there was failing tests."""

import argparse
import sys
from pathlib import Path
from typing import Tuple
from xml.etree import ElementTree


def get_results(results_xml_file: Path) -> Tuple[int, int]:
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

    num_tests = 0
    num_failed = 0

    tree = ElementTree.parse(results_xml_file)
    for ts in tree.iter("testsuite"):
        for tc in ts.iter("testcase"):
            num_tests += 1
            for _ in tc.iter("failure"):
                num_failed += 1

    return (num_tests, num_failed)


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
