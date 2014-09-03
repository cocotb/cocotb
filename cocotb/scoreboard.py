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
        self.log = SimLog("cocotb.scoreboard.%s" % self.dut.name)
        self.errors = 0
        self.expected = {}
        self._imm = fail_immediately

    @property
    def result(self):
        """Determine the test result - do we have any pending data remaining?"""
        fail = False
        for monitor, expected_output in self.expected.iteritems():
            if callable(expected_output):
                self.log.debug("Can't check all data returned for %s since expected output is \
                                callable function rather than a list" % str(monitor))
                continue
            if len(expected_output):
                self.log.warn("Still expecting %d transactions on %s" % (len(expected_output), str(monitor)))
                for index, transaction in enumerate(expected_output):
                    self.log.info("Expecting %d:\n%s" % (index, hexdump(str(transaction))))
                    if index > 5:
                        self.log.info("... and %d more to come" % (len(expected_output) - index - 1))
                        break
                fail = True
        if fail:
            return TestFailure("Not all expected output was received")
        if self.errors:
            return TestFailure("Errors were recorded during the test")
        return TestSuccess()

    def add_interface(self, monitor, expected_output, compare_fn=None):
        """Add an interface to be scoreboarded.

            Provides a function which the monitor will callback with received transactions

            Simply check against the expected output.

        """
        # save a handle to the expected output so we can check if all expected data has
        # been received at the end of a test.
        self.expected[monitor] = expected_output

        # Enforce some type checking as we only work with a real monitor
        if not isinstance(monitor, Monitor):
            raise TypeError("Expected monitor on the interface but got %s" % (monitor.__class__.__name__))

        if compare_fn is not None:
            if callable(compare_fn):
                monitor.add_callback(compare_fn)
                return
            raise TypeError("Expected a callable compare function but got %s" % str(type(compare_fn)))

        def check_received_transaction(transaction):
            """Called back by the monitor when a new transaction has been received"""

            log = logging.getLogger(self.log.name + '.' + monitor.name)

            if callable(expected_output):
                exp = expected_output(transaction)
            elif len(expected_output):
                exp = expected_output.pop(0)
            else:
                self.errors += 1
                log.error("Received a transaction but wasn't expecting anything")
                log.info("Got: %s" % (hexdump(str(transaction))))
                if self._imm: raise TestFailure("Received a transaction but wasn't expecting anything")
                return

            if type(transaction) != type(exp):
                self.errors += 1
                log.error("Received transaction is a different type to expected transaction")
                log.info("Got: %s but expected %s" % (str(type(transaction)), str(type(exp))))
                if self._imm: raise TestFailure("Received transaction of wrong type")
                return

            if transaction != exp:
                self.errors += 1
                log.error("Received transaction differed from expected output")
                log.info("Expected:\n" + hexdump(exp))
                if not isinstance(exp, str):
                    try:
                        for word in exp: self.log.info(str(word))
                    except: pass
                log.info("Received:\n" + hexdump(transaction))
                if not isinstance(transaction, str):
                    try:
                        for word in transaction: self.log.info(str(word))
                    except: pass
                log.warning("Difference:\n%s" % hexdiffs(exp, transaction))
                if self._imm: raise TestFailure("Received transaction differed from expected transaction")
            else:
                # Don't want to fail the test if we're passed something without __len__
                try:
                    log.debug("Received expected transaction %d bytes" % (len(transaction)))
                    log.debug(repr(transaction))
                except: pass

        monitor.add_callback(check_received_transaction)
