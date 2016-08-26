#!/usr/bin/env python
"""
Simple script to combine JUnit test results into a single XML file.

Useful for Jenkins.
"""

import os
import sys
import argparse
from xml.etree import cElementTree as ET


def find_all(name, path):
    result = []
    for root, dirs, files in os.walk(path):
        if name in files:
            yield os.path.join(root, name)

def get_parser():
    """Return the cmdline parser"""
    parser = argparse.ArgumentParser(description=__doc__,
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--directory", dest="directory", type=str, required=False,
                        default=".",
                        help="Name of base directory to search from")

    parser.add_argument("--output_file", dest="output_file", type=str, required=False,
                        default="combined_results.xml", 
                        help="Name of output file")
    parser.add_argument("--testsuites_name", dest="testsuites_name", type=str, required=False,
                        default="results", 
                        help="Name value for testsuites tag")
    parser.add_argument("--verbose", dest="debug", action='store_const', required=False,
                        const=True, default=False, 
                        help="Verbose/debug output")
    parser.add_argument("--suppress_rc", dest="set_rc", action='store_const', required=False,
                        const=False, default=True, 
                        help="Supress return code if failures found")
                    
    return parser


def main():
    
    parser = get_parser()
    args = parser.parse_args()
    rc = 0;
    
    result = ET.Element("testsuites", name=args.testsuites_name);
    
    for fname in find_all("results.xml", args.directory):
        if args.debug : print "Reading file %s" % fname
        tree = ET.parse(fname)
        for ts in tree.getiterator("testsuite"):
            if args.debug : print ("Ts name : %s, package : %s" % ( ts.get('name'), ts.get('package')))
            use_element = None
            for existing in result:
                if ((existing.get('name') == ts.get('name') and (existing.get('package') == ts.get('package')))):
                    if args.debug : print "Already found"
                    use_element=existing
                    break
            if use_element is None:
                result.append(ts)
            else:
                #for tc in ts.getiterator("testcase"):
                use_element.extend(list(ts));
            
    if args.debug : ET.dump(result)
    
    for testsuite in result.iter('testsuite'):
        for testcase in testsuite.iter('testcase'):
            for failure in testcase.iter('failure'):
                if args.set_rc: rc=1
                print "Failure in testsuite: '%s' testcase: '%s' with parameters '%s'" % (testsuite.get('name'), testcase.get('name'), testsuite.get('package'))
            
    
    ET.ElementTree(result).write(args.output_file, encoding="UTF-8")
    return rc
   
    

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
