#!/usr/bin/env python
"""
Simple script to combine JUnit test results into a single XML file.

Useful for Jenkins.

TODO: Pretty indentation
"""

import os
from xml.etree import cElementTree as ET

def find_all(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            yield os.path.join(root, name)

def main(path, output):

    testsuite = ET.Element("testsuite", name="all", package="all", tests="0")

    for fname in find_all("results.xml", path):
        tree = ET.parse(fname)
        for element in tree.iter("testcase"):
            testsuite.append(element)

    result = ET.Element("testsuites", name="results")
    result.append(testsuite)

    ET.ElementTree(result).write(output, encoding="UTF-8")

if __name__ == "__main__":
    main(".", "results.xml")

