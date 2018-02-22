''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET

import mmap
from io import StringIO

TRUNCATE_LINES = 100


# file from  http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
class File(StringIO):

    def countlines(self):
        buf = mmap.mmap(self.fileno(), 0)
        lines = 0
        while buf.readline():
            lines += 1
        return lines

    def head(self, lines_2find=1):
        self.seek(0)                            # Rewind file
        return [self.next() for x in range(lines_2find)]

    def tail(self, lines_2find=1):
        self.seek(0, 2)                         # go to end of file
        bytes_in_file = self.tell()
        lines_found, total_bytes_scanned = 0, 0
        while (lines_2find+1 > lines_found and
               bytes_in_file > total_bytes_scanned):
            byte_block = min(1024, bytes_in_file-total_bytes_scanned)
            self.seek(-(byte_block+total_bytes_scanned), 2)
            total_bytes_scanned += byte_block
            lines_found += self.read(1024).count('\n')
        self.seek(-total_bytes_scanned, 2)
        line_list = list(self.readlines())
        return line_list[-lines_2find:]


class XUnitReporter(object):

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

    def update_testsuite(self, testsuite=None, **kwargs):
        if testsuite is None:
            testsuite = self.last_testsuite
        for k in kwargs:
            testsuite.set(k, str(kwargs[k]))

    def update_testsuites(self, **kwargs):
        for k in kwargs:
            self.results.set(k, str(kwargs[k]))

    def add_log(self, logfile, testcase=None):
        if testcase is None:
            testcase = self.last_testcase
        log = SubElement(testcase, "system-out")
        f = File(logfile, 'r+')
        lines = f.countlines()
        if lines > (TRUNCATE_LINES * 2):
            head = f.head(TRUNCATE_LINES)
            tail = f.tail(TRUNCATE_LINES)
            log.text = "".join(head + list("[...truncated %d lines...]\n" %
                               ((lines - (TRUNCATE_LINES*2)))) + tail)
        else:
            log.text = "".join(f.readlines())

    def add_failure(self, testcase=None, **kwargs):
        if testcase is None:
            testcase = self.last_testcase
        log = SubElement(testcase, "failure", **kwargs)

    def add_skipped(self, testcase=None, **kwargs):
        if testcase is None:
            testcase = self.last_testcase
        log = SubElement(testcase, "skipped", **kwargs)

    def indent(self, elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def write(self):
        self.indent(self.results)
        ET.ElementTree(self.results).write(self.filename, encoding="UTF-8")
