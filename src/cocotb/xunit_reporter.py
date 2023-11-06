# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element, SubElement


class XUnitReporter:
    def __init__(self, filename="results.xml"):
        self.results = Element("testsuites", name="results")
        self.filename = filename

    def add_testsuite(self, **kwargs):
        self.last_testsuite = SubElement(self.results, "testsuite", **kwargs)
        return self.last_testsuite

    def add_testcase(self, testsuite=None, **kwargs):
        if testsuite is None:
            testsuite = self.last_testsuite
        self.last_testcase = SubElement(testsuite, "testcase", **kwargs)
        return self.last_testcase

    def add_property(self, testsuite=None, **kwargs):
        if testsuite is None:
            testsuite = self.last_testsuite
        self.last_property = SubElement(testsuite, "property", **kwargs)
        return self.last_property

    def add_failure(self, testcase=None, **kwargs):
        if testcase is None:
            testcase = self.last_testcase
        SubElement(testcase, "failure", **kwargs)

    def add_skipped(self, testcase=None, **kwargs):
        if testcase is None:
            testcase = self.last_testcase
        SubElement(testcase, "skipped", **kwargs)

    def indent(self, elem, level=0):
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def write(self):
        self.indent(self.results)
        ET.ElementTree(self.results).write(self.filename, encoding="UTF-8")
