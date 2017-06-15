''' Copyright (c) 2017 Sebastien Van Cauwenberghe <svancau@gmail.com>
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

import re
import sys
import cocotb
from cocotb.log import SimLog

"""
Everything related to requirement coverage in tests

This module checks for :req in the docstring of test functions. Multiple names can be used on the same line provided
 they are separated using commas.
 Requirements names are case sensitive.

Example:
    :req XXXX-0000, XXXX-0001
    :req XXXX-1234
"""


class Requirements:
    def __init__(self):
        self.requirement_status = {}
        self.log = SimLog("cocotb.requirements")

    def parse_docstring(self, in_docstr):
        """
        Takes a docstring as input and searches for ":req" tags followed by a requirement number or multiple
        requirements separated by commas.
        :param in_docstr: string containing the docstring
        :return: list containing the requirements found
        """
        if re.search('\n', in_docstr):
            docstr = in_docstr.split('\n')
        else:
            docstr = [in_docstr,]

        found = []
        for line in docstr:
            req = re.search(r'^\s*:req:?\s*(.*)$', line)
            if req:
                requirement = req.group(1)
                # Look for multiple items
                if re.search(r',', requirement):
                    for item in requirement.split(','):
                        found.append(item.strip())
                else:
                    found.append(requirement.strip())
        return found

    def update_requirements(self, running_test, test_result):
        """
        Updates the requirements status with the test status
        :param running_test: structure containing the running test information
        :param test_result: boolean containing if the test passed or not
        :return: None
        """
        if running_test.__doc__ != None:
            reqs = self.parse_docstring(running_test.__doc__)
            for item in reqs:
                if not item in self.requirement_status:
                    self.requirement_status[item] = []
                self.requirement_status[item].append((running_test.module, running_test.funcname, test_result))

    def log_requirements_summary(self):
        """
        Write the requirements list with the compliance status in the simulator output
        :return:
        """
        # Disabled when no requirements are found
        if not self.requirement_status:
            return
        LINE_LEN = 77
        LINE_SEP = "*"*LINE_LEN+"\n"
        summary = LINE_SEP
        summary += '** {a:50} {b:20} **\n'.format(a='REQUIREMENT', b='COMPLIANT')
        summary += LINE_SEP
        for requirement, result in sorted(self.requirement_status.items()):
            n_ok = 0
            n_nok = 0
            for test_result in result:
                if test_result[2]:
                    n_ok += 1
                else:
                    n_nok += 1
            status = 'COMPLIANT' if n_nok == 0 else 'NOT COMPLIANT' if n_ok == 0 else 'PARTIALLY COMPLIANT'
            summary += '** {a:50} {b:20} **\n'.format(a=requirement, b=status)
        summary += LINE_SEP
        self.log.info(summary)

    def write_requirement_coverage(self, filename='requirements.cov'):
        """
        Write a JSON file containing the requirement number alongside all the relevant tests and test results
        :param filename: Name of the requirement output file containing the json output
        :return: None
        """
        # Disabled when no requirements are found
        if not self.requirement_status:
            return

        try:
            import json
        except ImportError as e:
            msg = ("JSON module not found, requirements list not written"
                   "\n"
                   "Import error was: %s\n" % repr(e))
            sys.stderr.write(msg)
            sys.stderr.flush()
            return

        with open(filename, 'w') as fd:
            json.dump(self.requirement_status, fd)
