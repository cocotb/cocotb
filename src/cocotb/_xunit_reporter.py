# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import xml.etree.ElementTree as ET
from typing import Union
from xml.etree.ElementTree import Element, SubElement


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

    def indent(self, elem: Element, level: int = 0) -> None:
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for sub_elem in elem:
                self.indent(sub_elem, level + 1)
            if not sub_elem.tail or not sub_elem.tail.strip():
                sub_elem.tail = i
        elif level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

    def write(self) -> None:
        self.indent(self.results)
        ET.ElementTree(self.results).write(self.filename, encoding="UTF-8")
