# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import re
import sys
import xml.etree.ElementTree as ET
from typing import Union
from xml.etree.ElementTree import Element, SubElement


# Shamelessly ripped from pytest source code.
# https://github.com/pytest-dev/pytest/blob/d036b12bb6fa09f9a8a3b690cc7336113c93fa44/src/_pytest/junitxml.py#L37C1-L61C50
def bin_xml_escape(arg: object) -> str:
    r"""Visually escape invalid XML characters.

    For example, transforms
        'hello\aworld\b'
    into
        'hello#x07world#x08'
    Note that the #xABs are *not* XML escapes - missing the ampersand &#xAB.
    The idea is to escape visually for the user rather than for XML itself.
    """

    def repl(matchobj: "re.Match[str]") -> str:
        i = ord(matchobj.group())
        if i <= 0xFF:
            return f"#x{i:02X}"
        else:
            return f"#x{i:04X}"

    # The spec range of valid chars is:
    # Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # For an unknown(?) reason, we disallow #x7F (DEL) as well.
    illegal_xml_re = (
        "[^\u0009\u000a\u000d\u0020-\u007e\u0080-\ud7ff\ue000-\ufffd\u10000-\u10ffff]"
    )
    return re.sub(illegal_xml_re, repl, str(arg))


if sys.version_info < (3, 9):

    def indent(elem: Element, level: int = 0) -> None:
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for sub_elem in elem:
                indent(sub_elem, level + 1)
            if not sub_elem.tail or not sub_elem.tail.strip():
                sub_elem.tail = i
        elif level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

else:
    from xml.etree.ElementTree import indent


class XUnitReporter:
    last_testsuite: Element
    last_testcase: Element

    def __init__(self, filename: str = "results.xml") -> None:
        self.results = Element("testsuites", name="results")
        self.filename = filename

    def add_testsuite(self, **kwargs: str) -> Element:
        self.last_testsuite = SubElement(self.results, "testsuite", kwargs)
        return self.last_testsuite

    def add_testcase(
        self, testsuite: Union[Element, None] = None, **kwargs: str
    ) -> Element:
        if testsuite is None:
            testsuite = self.last_testsuite
        self.last_testcase = SubElement(testsuite, "testcase", kwargs)
        return self.last_testcase

    def add_property(
        self, testsuite: Union[Element, None] = None, **kwargs: str
    ) -> Element:
        if testsuite is None:
            testsuite = self.last_testsuite
        self.last_property = SubElement(testsuite, "property", kwargs)
        return self.last_property

    def add_failure(self, testcase: Union[Element, None] = None, **kwargs: str) -> None:
        if testcase is None:
            testcase = self.last_testcase
        SubElement(testcase, "failure", kwargs)

    def add_skipped(self, testcase: Union[Element, None] = None, **kwargs: str) -> None:
        if testcase is None:
            testcase = self.last_testcase
        SubElement(testcase, "skipped", kwargs)

    def write(self) -> None:
        indent(self.results)
        ET.ElementTree(self.results).write(self.filename, encoding="UTF-8")
