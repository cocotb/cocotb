#!/usr/bin/env python
"""
Simple script to report JUnit test results

"""

from __future__ import print_function
import sys

def report_results(xml_filename):
    xunitparser = None
    try:
        import xunitparser
    except ImportError as e:
        sys.stderr.write("xunitparser module not availble results report not avaliable\n")
        sys.stderr.write("Import error was: %s\n" % repr(e))

     
    if xunitparser is not None:
        ts, tr = xunitparser.parse(open(xml_filename))
        report = {'skipped': len(tr.skipped), 'failed': len(tr.failures), 'errored': len(tr.errors), 'all': tr.testsRun}
        
        print('Test Report:', report)
        if report['failed'] or report['errored'] or not report['all']:
            return 1
        
        return 0

if __name__ == "__main__":
    if len(sys.argv) is not 2:
        print("Please specify a result file")
        exit(1)
        
    exit(report_results(sys.argv[1]))

    
