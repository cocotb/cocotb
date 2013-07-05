from xml.etree.ElementTree import Element, SubElement
import xml.etree.ElementTree as ET

TRUNCATE_LINES = 100

# file from  http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
class File(file):

    def countlines(self):
        buf = mmap.mmap(self.fileno(), 0)
        lines = 0
        while buf.readline():
            lines += 1
        return lines

    def head(self, lines_2find=1):
        self.seek(0)                            #Rewind file
        return [self.next() for x in xrange(lines_2find)]

    def tail(self, lines_2find=1):
        self.seek(0, 2)                         #go to end of file
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


class XUnitReporter:

    def __init__(self, filename="results.xml"):
        self.results = Element("testsuites", name="results")

    def add_testsuite(self, **kwargs):
        self.last_testsuite = SubElement(self.results, "testsuite", **kwargs)
        return self.last_testsuite

    def add_testcase(self, testsuite=None, **kwargs):
        if testsuite == None:
            testsuite = self.last_testsuite
        self.last_testcase = SubElement(testsuite, "testcase", **kwargs)
        return self.last_testcase

    def update_testsuite(self, testsuite=None, **kwargs):
        if testsuite == None:
            testsuite = self.last_testsuite
        for k in kwargs:
            testsuite.set(k, str(kwargs[k]))

    def update_testsuites(self, **kwargs):
        for k in kwargs:
            self.results.set(k, str(kwargs[k]))

    def add_log(self, logfile, testcase=None):
        if testcase == None:
            testcase = self.last_testcase
        log = SubElement(testcase, "system-out")
        f = File(logfile, 'r+')
        lines = f.countlines()
        if lines > (TRUNCATE_LINES * 2):
            head = f.head(TRUNCATE_LINES)
            tail = f.tail(TRUNCATE_LINES)
            log.text = "".join(head + list("[...truncated %d lines...]\n" % ( (lines - (TRUNCATE_LINES*2)) )) + tail)
        else:
            log.text = "".join(f.readlines())

    def add_failure(self, testcase=None, **kwargs):
        if testcase == None:
            testcase = self.last_testcase
        log = SubElement(testcase, "failure", **kwargs)


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
        print 'Capturing results to ', self.filename
        self.indent(self.results)
        ET.ElementTree(self.results).write(self.filename, xml_declaration = True, method = "xml", encoding="UTF-8")

