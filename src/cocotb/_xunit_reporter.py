# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import xml.etree.ElementTree as ET
from typing import Dict, Union
from xml.etree.ElementTree import Element, SubElement


class XUnitReporter:
    last_testsuite: Element
    last_testcase: Element
    _testsuite_stats: Dict[int, Dict[str, Union[int, float]]]

    def __init__(self, filename: str = "results.xml") -> None:
        self.results = Element("testsuites", name="results")
        self.filename = filename
        self._testsuite_stats = {}
        self.add_testsuite()

    def add_testsuite(self, **kwargs: str) -> Element:
        """Initialize required JUnit attributes with defaults"""
        testsuite_attrs = {
            "tests": "0",
            "failures": "0",
            "errors": "0",
            "time": "0",
            **kwargs,
        }
        self.last_testsuite = SubElement(self.results, "testsuite", testsuite_attrs)

        testsuite_id = id(self.last_testsuite)
        self._testsuite_stats[testsuite_id] = {
            "tests": 0,
            "failures": 0,
            "errors": 0,
            "time": 0.0,
        }

        return self.last_testsuite

    def add_testcase(
        self, testsuite: Union[Element, None] = None, **kwargs: str
    ) -> Element:
        if testsuite is None:
            testsuite = self.last_testsuite
        standard_attrs = {
            k: v for k, v in kwargs.items() if k in ["name", "classname", "time"]
        }
        # move non-standard attrs to properties
        properties = {
            k: v for k, v in kwargs.items() if k not in ["name", "classname", "time"]
        }

        self.last_testcase = SubElement(testsuite, "testcase", standard_attrs)

        if properties:
            props_elem = SubElement(self.last_testcase, "properties")
            [
                SubElement(props_elem, "property", name=k, value=str(v))
                for k, v in properties.items()
            ]

        # testsuite stats need to be updated now
        testsuite_id = id(testsuite)
        if testsuite_id in self._testsuite_stats:
            self._testsuite_stats[testsuite_id]["tests"] += 1
            if "time" in kwargs:
                try:
                    time_val = float(kwargs["time"])
                    self._testsuite_stats[testsuite_id]["time"] += time_val
                except (ValueError, TypeError):
                    pass

        return self.last_testcase

    def add_property(
        self, testsuite: Union[Element, None] = None, **kwargs: str
    ) -> Element:
        if testsuite is None:
            testsuite = self.last_testsuite
        properties = testsuite.find("properties") or SubElement(testsuite, "properties")
        return SubElement(properties, "property", kwargs)

    def add_failure(self, testcase: Union[Element, None] = None, **kwargs: str) -> None:
        if testcase is None:
            testcase = self.last_testcase
        SubElement(testcase, "failure", kwargs)
        # update failure count for parent testsuite
        testsuite = next(
            (ts for ts in self.results.findall("testsuite") if testcase in ts), None
        )
        if testsuite and id(testsuite) in self._testsuite_stats:
            self._testsuite_stats[id(testsuite)]["failures"] += 1

    def add_skipped(self, testcase: Union[Element, None] = None, **kwargs: str) -> None:
        if testcase is None:
            testcase = self.last_testcase
        SubElement(testcase, "skipped", kwargs)

    def _update_testsuite_attributes(self) -> None:
        """Update testsuite elements with correct statistics before writing."""
        for testsuite in self.results.findall("testsuite"):
            stats = self._testsuite_stats.get(id(testsuite))
            if stats:
                testsuite.attrib.update(
                    {
                        "tests": str(stats["tests"]),
                        "failures": str(stats["failures"]),
                        "errors": str(stats["errors"]),
                        "time": f"{stats['time']:.6f}",
                    }
                )

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
        self._update_testsuite_attributes()
        self.indent(self.results)
        ET.ElementTree(self.results).write(self.filename, encoding="UTF-8")
