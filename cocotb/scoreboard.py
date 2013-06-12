#!/usr/bin/env python

''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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
from cocotb.utils import hexdiffs

from cocotb.monitor import Monitor

class Scoreboard(object):
    """Generic scorboarding class

    We can add interfaces by providing a monitor and an expected output queue

    The expected output can either be a function which provides a transaction
    or a simple list containing the expected output.

    TODO:
        Statistics for end-of-test summary etc.
    """

    def __init__(self, dut, reorder_depth=0):
        self.dut = dut
        self.log = logging.getLogger("cocotb.scoreboard.%s" % self.dut.name)

    def add_interface(self, monitor, expected_output):
        """Add an interface to be scoreboarded.

            Provides a function which the monitor will callback with received transactions

            Simply check against the expected output.

        """

        # Enforce some type checking as we only work with a real monitor
        if not isinstance(monitor, Monitor):
            raise TypeError("Expected monitor on the interface but got %s" % (monitor.__class__.__name__))

        def check_received_transaction(transaction):
            """Called back by the monitor when a new transaction has been received"""

            if not expected_output:
                self.log.error("%s" % (transaction))    # TODO hexdump
                raise TestFailure("Recieved a transaction but wasn't expecting anything")

            if callable(expected_output): exp = expected_output()
            else: exp = expected_output.pop(0)

            if transaction != exp:
                self.log.error("Received transaction differed from expected output")
                self.log.warning(hexdiffs(exp, transaction))
            else:
                self.log.debug("Received expected transaction %d bytes" % (len(transaction)))
                self.log.debug(repr(transaction))

        monitor.add_callback(check_received_transaction)
