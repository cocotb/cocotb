#!/usr/bin/env python

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

"""
    Common scoreboarding capability.
"""
import logging
import cocotb

from cocotb.utils import hexdump, hexdiffs
from cocotb.log import SimLog
from cocotb.monitors import Monitor
from cocotb.result import TestFailure, TestSuccess


class Scoreboard(object):
    """Generic scoreboarding class

    We can add interfaces by providing a monitor and an expected output queue

    The expected output can either be a function which provides a transaction
    or a simple list containing the expected output.

    TODO:
        Statistics for end-of-test summary etc.
    """

    def __init__(self, dut, reorder_depth=0, fail_immediately=True):
        self.dut = dut
        self.log = SimLog("cocotb.scoreboard.%s" % self.dut._name)
        self.errors = 0
        self.expected = {}
        self._imm = fail_immediately

    @property
    def result(self):
        """Determine the test result, do we have any pending data remaining?"""
        fail = False
        for monitor, expected_output in self.expected.items():
            if callable(expected_output):
                self.log.debug("Can't check all data returned for %s since "
                               "expected output is callable function rather "
                               "than a list" % str(monitor))
                continue
            if len(expected_output):
                self.log.warn("Still expecting %d transactions on %s" %
                              (len(expected_output), str(monitor)))
                for index, transaction in enumerate(expected_output):
                    self.log.info("Expecting %d:\n%s" %
                                  (index, hexdump(str(transaction))))
                    if index > 5:
                        self.log.info("... and %d more to come" %
                                      (len(expected_output) - index - 1))
                        break
                fail = True
        if fail:
            return TestFailure("Not all expected output was received")
        if self.errors:
            return TestFailure("Errors were recorded during the test")
        return TestSuccess()

    def compare(self, got, exp, log, strict_type=True):
        """
        Common function for comparing two transactions.

        Can be re-implemented by a subclass.
        """

        # Compare the types
        if strict_type and type(got) != type(exp):
            self.errors += 1
            log.error("Received transaction is a different type to expected "
                      "transaction")
            log.info("Got: %s but expected %s" %
                     (str(type(got)), str(type(exp))))
            if self._imm:
                raise TestFailure("Received transaction of wrong type")
            return
        # Or convert to a string before comparison
        elif not strict_type:
            got, exp = str(got), str(exp)

        # Compare directly
        if got != exp:
            self.errors += 1

            # Try our best to print out something useful
            strgot, strexp = str(got), str(exp)

            log.error("Received transaction differed from expected output")
            if not strict_type:
                log.info("Expected:\n" + hexdump(strexp))
            else:
                log.info("Expected:\n" + repr(exp))
            if not isinstance(exp, str):
                try:
                    for word in exp:
                        log.info(str(word))
                except:
                    pass
            if not strict_type:
                log.info("Received:\n" + hexdump(strgot))
            else:
                log.info("Received:\n" + repr(got))
            if not isinstance(got, str):
                try:
                    for word in got:
                        log.info(str(word))
                except:
                    pass
            log.warning("Difference:\n%s" % hexdiffs(strexp, strgot))
            if self._imm:
                raise TestFailure("Received transaction differed from expected"
                                  "transaction")
        else:
            # Don't want to fail the test
            # if we're passed something without __len__
            try:
                log.debug("Received expected transaction %d bytes" %
                          (len(got)))
                log.debug(repr(got))
            except:
                pass

    def add_interface(self, monitor, expected_output, compare_fn=None,
                      reorder_depth=0, strict_type=True):
        """Add an interface to be scoreboarded.

            Provides a function which the monitor will callback with received
            transactions

            Simply check against the expected output.

        """
        # save a handle to the expected output so we can check if all expected
        # data has been received at the end of a test.
        self.expected[monitor] = expected_output

        # Enforce some type checking as we only work with a real monitor
        if not isinstance(monitor, Monitor):
            raise TypeError("Expected monitor on the interface but got %s" %
                            (monitor.__class__.__name__))

        if compare_fn is not None:
            if callable(compare_fn):
                monitor.add_callback(compare_fn)
                return
            raise TypeError("Expected a callable compare function but got %s" %
                            str(type(compare_fn)))

        self.log.info("Created with reorder_depth %d" % reorder_depth)

        def check_received_transaction(transaction):
            """Called back by the monitor when a new transaction has been
            received"""

            if monitor.name:
                log_name = self.log.name + '.' + monitor.name
            else:
                log_name = self.log.name + '.' + monitor.__class__.__name__

            log = logging.getLogger(log_name)

            if callable(expected_output):
                exp = expected_output(transaction)

            elif len(expected_output):
                for i in range(min((reorder_depth + 1), len(expected_output))):
                    if expected_output[i] == transaction:
                        break
                else:
                    i = 0
                exp = expected_output.pop(i)
            else:
                self.errors += 1
                log.error("Received a transaction but wasn't expecting "
                          "anything")
                log.info("Got: %s" % (hexdump(str(transaction))))
                if self._imm:
                    raise TestFailure("Received a transaction but wasn't "
                                      "expecting anything")
                return

            self.compare(transaction, exp, log, strict_type=strict_type)

        monitor.add_callback(check_received_transaction)
