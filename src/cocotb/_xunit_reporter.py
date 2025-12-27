# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""xUnit XML reporter."""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from platform import node
from traceback import format_exception
from typing import Literal
from xml.etree.ElementTree import Element, ElementTree, SubElement, indent

Family = Literal["legacy", "xunit1", "xunit2"]
"""Name of xUnit family.

- ``legacy`` - Alias to ``xunit1``.
- ``xunit1`` - With ``file`` and ``line`` attributes in test case.
- ``xunit2`` - Without ``file`` and ``line`` attributes in test case.
"""

Environment = Literal["github", "gitlab", "jenkins"]
"""Name of environment, mostly CI.

- ``github`` - GitHub Actions.
- ``gitlab`` - GitLab CI.
- ``jenkins`` - Jenkins CI.
"""

# The spec range of valid chars is:
# Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
# For an unknown(?) reason, we disallow #x7F (DEL) as well.
_INVALID_CHARS: re.Pattern[str] = re.compile(
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
        environment: Environment | None = None,
        family: Family | None = None,
        workspace: Path | str | None = None,
        **kwargs: object,
    ) -> None:
        """Create new instance of xUnit reporter.

        Args:
            name:        Name of xUnit reporter.
            environment: Name of environment where tests are running. If not provided, it will be detected automatically.
            family:      Name of xUnit family. If not provided, it will be detected based on environment.
            workspace:   Path where tests are running. If not provided, it will be detected based on environment.
            kwargs:      Default properties for all created test suites.
        """
        self._root: Element = Element("testsuites", name=name)
        self._testsuite: TestSuite | None = None
        self._testsuites: dict[str, TestSuite] = {}
        self._environment: Environment | None = environment or _detect_environment()
        self._family: Family = family or _get_family(self._environment)
        self._properties: dict[str, object] = dict(kwargs)
        self._workspace: Path = Path(
            workspace or _get_workspace(self._environment)
        ).resolve()

    @property
    def workspace(self) -> Path:
        """Absolute path to the workspace where tests are running."""
        return self._workspace

    @property
    def family(self) -> Family:
        """Name of xUnit family."""
        return self._family

    @property
    def environment(self) -> Environment | None:
        """Name of environment where tests are running."""
        return self._environment

    def add_testcase(
        self,
        name: str,
        classname: str = "",
        file: Path | str = "",
        line: int = 0,
        time: int | float = 0,
        system_out: str | None = None,
        system_err: str | None = None,
        attachments: Sequence[Path | str] | None = None,
        failure: bool | str | BaseException | None = None,
        error: bool | str | BaseException | None = None,
        skipped: bool | str | None = None,
        **kwargs: object,
    ) -> None:
        """Create and add new test case to test suite.

        Args:
            name:        Name of test.
            classname:   Path to module (using the ``.`` dot as separator) where test is located.
            file:        Path to file with test.
            line:        Line number of test in file.
            time:        Real-time execution of test in seconds.
            system_out:  Captured standard output from test case. It will also include XML file attachments.
            system_err:  Captured standard error from test case.
            attachments: List of attachments to add.
            failure:     Fail test case.
            error:       Error test case.
            skipped:     Skip test case.
            kwargs:      Additional testcase properties.
        """
        testsuite: TestSuite = self._get_testsuite(classname or "cocotb")

        attributes: dict[str, str] = {
            "classname": _escape(classname),
            "name": _escape(name),
            "time": f"{time:.3f}",
        }

        if self._family in ("legacy", "xunit1"):
            attributes["file"] = _escape(self._normalize_path(file)) if file else ""
            attributes["line"] = str(line)

        testsuite.time += time
        testsuite.tests += 1

        testcase: Element = SubElement(testsuite.element, "testcase", attrib=attributes)

        if file or line or kwargs or attachments:
            properties: Element = SubElement(testcase, "properties")

            if file:
                _add_property(properties, "file", self._normalize_path(file))

            if line:
                _add_property(properties, "line", line)

            for key, value in kwargs.items():
                _add_property(properties, key, value)

            if attachments:
                if system_out is None:
                    system_out = ""

                # Ensure a newline when adding attachments
                if system_out and not system_out.endswith(os.linesep):
                    system_out += os.linesep

            for attachment in attachments or ():
                path = self._normalize_path(attachment)
                _add_property(properties, "attachment", path)
                system_out = f"{system_out}[[ATTACHMENT|{path}]]{os.linesep}"

        if failure:
            self._add_simple(testcase, "failure", failure)
            testsuite.failures += 1

        if error:
            self._add_simple(testcase, "error", error)
            testsuite.errors += 1

        if skipped:
            self._add_simple(testcase, "skipped", skipped)
            testsuite.skipped += 1

        if system_out:
            SubElement(testcase, "system-out").text = self._normalize_text(system_out)

        if system_err:
            SubElement(testcase, "system-err").text = self._normalize_text(system_err)

    def write(self, filename: Path | str) -> None:
        """Write xUnit report to file.

        Args:
            filename: Path to file where to write tests results.
        """
        for testsuite in self._testsuites.values():
            testsuite.update()

        # Create directory
        Path(filename).parent.mkdir(0o700, parents=True, exist_ok=True)

        indent(self._root)
        ElementTree(self._root).write(
            str(filename),
            encoding="utf-8",
            xml_declaration=True,
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

        testsuite: Element = SubElement(
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

        if self._properties:
            properties: Element = SubElement(testsuite, "properties")

            for key, value in self._properties.items():
                _add_property(properties, key, value)

        return self._testsuite

    def _normalize_path(self, path: Path | str) -> Path:
        """Convert provided path to relative path."""
        if not isinstance(path, Path):
            path = Path(path)

        if not path.is_absolute():
            return path

        try:
            return path.resolve().relative_to(self._workspace)
        except ValueError:
            return path.resolve()

    def _add_simple(
        self,
        parent: Element,
        name: str,
        arg: bool | str | BaseException | None = None,
    ) -> Element:
        """Create and add a simple XML element to XML parent.

        Args:
            parent:  XML parent element.
            name:    Name of XML element.
            arg:     Argument of XML element.

        Returns:
            Added XML element.
        """
        message: str = _escape(arg).strip()

        if message:
            message = message.splitlines()[0]

        if isinstance(arg, BaseException):
            kind: str = _escape(type(arg).__name__)
            element: Element = SubElement(parent, name, message=message, type=kind)
            text: str = self._normalize_text(
                "".join(format_exception(type(arg), arg, arg.__traceback__))
            )

            if text:
                element.text = text

            return element

        if isinstance(arg, str) and message:
            return SubElement(parent, name, message=message)

        return SubElement(parent, name)

    def _normalize_text(self, text: str) -> str:
        """Replace all absolute paths with relative ones."""
        return _escape(text.replace(f"{self._workspace}{os.path.sep}", ""))


def _detect_environment() -> Environment | None:
    """Try to detect environment based on environment variables.

    Args:
        Detected environment or None if cannot determine it.
    """
    # https://docs.github.com/en/actions/reference/workflows-and-actions/variables#default-environment-variables
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github"

    # https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
    if os.environ.get("GITLAB_CI") == "true":
        return "gitlab"

    # https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#using-environment-variables
    if os.environ.get("BUILD_TAG", "").startswith("jenkins-"):
        return "jenkins"

    return None


def _get_family(environment: Environment | None) -> Family:
    """Get xUnit family.

    Args:
        environment: Name of environment where tests are running.

    Returns:
        xUnit family.
    """
    if environment in ("gitlab",):
        return "xunit1"

    return "xunit2"


def _get_workspace(environment: Environment | None) -> Path:
    """Get the absolute path to the workspace where tests are running.

    Args:
        environment: Name of environment where tests are running.

    Returns:
        Absolute path to the workspace where tests are running.
    """
    # https://docs.github.com/en/actions/reference/workflows-and-actions/variables#default-environment-variables
    if environment == "github":
        return Path(os.environ.get("GITHUB_WORKSPACE", "."))

    # https://docs.gitlab.com/ci/variables/predefined_variables/#predefined-variables
    if environment == "gitlab":
        return Path(os.environ.get("CI_PROJECT_DIR", "."))

    # https://www.jenkins.io/doc/book/pipeline/jenkinsfile/#using-environment-variables
    if environment == "jenkins":
        return Path(os.environ.get("WORKSPACE", "."))

    return Path.cwd()


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


def _add_property(parent: Element, name: str, value: object) -> None:
    """Add property to XML element.

    Args:
        parent: XML parent element.
        name:   Name of property.
        value:  Value of property.
    """
    SubElement(parent, "property", name=_escape(name), value=_escape(value))
