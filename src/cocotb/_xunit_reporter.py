# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""xUnit XML reporter.

The reporter generates XML results files compatible with `Jenkins xUnit schema in Jenkins version 2.4.0
<https://github.com/jenkinsci/xunit-plugin/blob/xunit-2.4.0/src/main/resources/org/jenkinsci/plugins/xunit/types/model/xsd/junit-10.xsd>`_
and with JUnit XML test report files from pytest when used with ``junit_family=xunit2`` pytest option.

This allow to support wide range of different CI environments like GitHub Actions, GitLab CI, Jenkins CI and others.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from platform import node
from traceback import format_exception
from typing import Any, Literal
from xml.etree.ElementTree import Element, ElementTree, SubElement

Status = Literal["passed", "failed", "skipped", "error"]
"""Status of test case.

- ``passed`` - Test passed.
- ``failed`` - Test failed. Test case will include the ``failure`` XML element.
- ``skipped`` - Test was skipped. Test case will include the ``skipped`` XML element.
- ``error`` - An unexpected error when test was executed. Test case will include the ``error`` XML element.
"""


# The spec range of valid chars is:
# Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
# For an unknown(?) reason, we disallow #x7F (DEL) as well.
_INVALID_CHARS = re.compile(
    "[^\u0009\u000a\u000d\u0020-\u007e\u0080-\ud7ff\ue000-\ufffd\u10000-\u10ffff]",
)


class TestSuite:
    """xUnit test suite."""

    def __init__(self, element: Element) -> None:
        """Create new instance of test suite.

        Args:
            element: XML element of test suite.
        """
        self.element: Element = element
        self.errors: int = 0
        self.failures: int = 0
        self.skipped: int = 0
        self.tests: int = 0
        self.time: float = 0.0

    def update(self) -> None:
        """Update all test suite statistic counters."""
        self.element.set("errors", str(self.errors))
        self.element.set("failures", str(self.failures))
        self.element.set("skipped", str(self.skipped))
        self.element.set("tests", str(self.tests))
        self.element.set("time", f"{self.time:.3f}")


class XUnitReporter:
    """xUnit reporter."""

    def __init__(
        self,
        name: str = "cocotb tests",
        relative_to: Path | str | None = None,
        default_properties: Mapping[str, Any] | None = None,
        default_attachments: Iterable[Path | str] | None = None,
    ) -> None:
        """Create new instance of xUnit reporter.

        Args:
            name: Name of xUnit reporter. Used as name for the XML test suites root element.
            relative_to: If provided, all reported absolute paths will be converted to relative paths.
            default_properties: Additional common default properties that will be added to all created test cases.
            default_attachments: Additional common default file attachments that will be added to all created test cases.
        """
        # The root of the XML document
        self._root = Element("testsuites", name=name)

        # Current tracked test suite element
        self._testsuite: TestSuite | None = None

        # List of all created and cached test suite elements
        self._testsuites: dict[str, TestSuite] = {}

        # Common properties that will be added to all created test cases
        self._default_properties = dict(default_properties or {})

        # If present, all reported absolute paths will be converted to relative paths
        self._relative_to = Path(relative_to).resolve() if relative_to else None
        self._relative_to_str = f"{self._relative_to}{os.path.sep}"

        # Common file attachments that will be added to all created test cases
        self._default_attachments: list[str] = [
            self._normalize_path(attachment) for attachment in default_attachments or ()
        ]

        # A text block with a list of file attachments separated by a newline
        self._text_attachments: str = "\n".join(
            f"[[ATTACHMENT|{attachment}]]" for attachment in self._default_attachments
        )

    def add_testcase(
        self,
        name: str,
        classname: str,
        status: Status,
        time: int | float = 0,
        system_out: str = "",
        system_err: str = "",
        reason: str | BaseException | None = None,
        extra_properties: Mapping[str, Any] | None = None,
    ) -> None:
        """Create and add new test case to test suite.

        Args:
            name: Name of test.
            classname: Path to module (using the ``.`` dot as separator) where test is located.
            status: Status of test case.
            time: Wall clock execution time of test in seconds.
            system_out: Text that will be included in the ``system-out`` element. It will also include XML file attachments.
            system_err: Text that will be included in the ``system-err`` element.
            reason: Reason of failed or skipped test case.
            extra_properties: Additional test case properties.
        """
        testsuite = self._get_testsuite(classname or "cocotb")
        testsuite.time += time
        testsuite.tests += 1

        # NOTE: file and line attributes are invalid in Jenkins XML schema version 2.*
        testcase = SubElement(
            testsuite.element,
            "testcase",
            classname=_escape(classname),
            name=_escape(name),
            time=f"{time:.3f}",
        )

        properties = self._default_properties.copy()

        if extra_properties:
            properties.update(extra_properties)

        properties_root = SubElement(testcase, "properties")

        for key, item in properties.items():
            value = self._normalize_path(item) if key == "file" else str(item)
            properties_root.append(Element("property", name=key, value=value))

        for value in self._default_attachments:
            properties_root.append(Element("property", name="attachment", value=value))

        if status == "skipped":
            self._add_simple(testcase, "skipped", reason)
            testsuite.skipped += 1

        elif status == "error":
            self._add_simple(testcase, "error", reason)
            testsuite.errors += 1

        elif status == "failed":
            self._add_simple(testcase, "failure", reason)
            testsuite.failures += 1

        if self._text_attachments:
            system_out = _ensure_newline(system_out) + self._text_attachments

        if system_out:
            SubElement(testcase, "system-out").text = self._normalize_text(system_out)

        if system_err:
            SubElement(testcase, "system-err").text = self._normalize_text(system_err)

    def write(self, filename: Path | str) -> None:
        """Write xUnit report to file.

        Args:
            filename: Path to file where to write tests results.
        """
        # Update all statistic counters in all test suites
        for testsuite in self._testsuites.values():
            testsuite.update()

        # Create directory
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        ElementTree(self._root).write(
            str(filename), encoding="utf-8", xml_declaration=True
        )

    def _get_testsuite(self, name: str) -> TestSuite:
        """Create and add new test suite to list of test suites.

        Args:
            name: Name of test suite.

        Returns:
            Created new test suite instance.
        """
        self._testsuite = self._testsuites.get(name)

        if self._testsuite:
            return self._testsuite

        testsuite = SubElement(
            self._root,
            "testsuite",
            name=_escape(name),
            errors="0",
            failures="0",
            skipped="0",
            tests="0",
            time="0",
            timestamp=_escape(datetime.now(timezone.utc).isoformat()),
            hostname=_escape(node()),
        )

        self._testsuite = TestSuite(testsuite)
        self._testsuites[name] = self._testsuite  # cache it

        return self._testsuite

    def _normalize_path(self, path: Any) -> str:
        """Convert provided path to relative path."""
        if self._relative_to:
            try:
                return str(Path(path).resolve().relative_to(self._relative_to))
            except ValueError:
                pass

        return str(path)

    def _add_simple(
        self,
        parent: Element,
        name: str,
        reason: str | BaseException | None = None,
    ) -> Element:
        """Create and add a simple XML element to XML parent.

        Args:
            parent: XML parent element.
            name: Name of XML element.
            reason: Reason to be included in created XML element.

        Returns:
            Added XML element.
        """
        if isinstance(reason, BaseException):
            kind = _escape(type(reason).__name__)
            element = SubElement(parent, name, message=_escape(reason), type=kind)
            text = self._normalize_text(
                "".join(format_exception(type(reason), reason, reason.__traceback__))
            )

            if text:
                element.text = text

            return element

        if reason:
            return SubElement(parent, name, message=_escape(reason))

        return SubElement(parent, name)

    def _normalize_text(self, text: str) -> str:
        """Normalize provided text.

        * Replacing all absolute paths with relative ones.
        * Replacing Windows/macOS newlines with POSIX newlines.
        * Ensuring a newline at the end of the text.
        * Removing invalid characters.

        Returns:
            Normalized text.
        """
        if self._relative_to:
            text = text.replace(self._relative_to_str, "")

        if "\r" in text:
            text = text.replace("\r\n", "\n").replace("\r", "\n")

        return _escape(_ensure_newline(text))


def _ensure_newline(text: str) -> str:
    """Ensure newline at the end of the provided text."""
    return text + "\n" if text and text[-1] != "\n" else text


def _escape_code(matchobj: re.Match[str]) -> str:
    """Visually escape invalid XML character."""
    value = ord(matchobj.group())

    if value <= 0xFF:
        return f"#x{value:02X}"
    else:
        return f"#x{value:04X}"


# Shamelessly ripped from pytest source code.
# https://github.com/pytest-dev/pytest/blob/d036b12bb6fa09f9a8a3b690cc7336113c93fa44/src/_pytest/junitxml.py#L37C1-L61C50
def _escape(arg: object) -> str:
    r"""Visually escape invalid XML characters.

    For example, transforms
        'hello\aworld\b'
    into
        'hello#x07world#x08'
    Note that the #xABs are *not* XML escapes - missing the ampersand &#xAB.
    The idea is to escape visually for the user rather than for XML itself.
    """
    return _INVALID_CHARS.sub(_escape_code, str(arg))
