''' Copyright (c) 2015 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd
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

import logging

import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestError, TestFailure


def recursive_dump(parent, log):
    """
    Recursively iterate through every object and log a message

    Returns a count of the total number of objects found
    """
    count = 0
    for thing in parent:
        count += 1
        log.info("Found %s.%s (%s)", parent._name, thing._name, type(thing))
        count += recursive_dump(thing, log)
    return count


@cocotb.test()
def recursive_discovery(dut):
    """
    Recursively discover every single object in the design
    """
    tlog = logging.getLogger("cocotb.test")
    yield Timer(100)
    total = recursive_dump(dut, tlog)
    tlog.info("Found a total of %d things", total)

    if not isinstance(dut.i_verilog.uart1.baud_gen_1.baud_freq, cocotb.handle.ModifiableObject):
        tlog.error("Expected dut.i_verilog.uart1.baud_gen_1.baud_freq to be modifiable")
        tlog.error("but it was %s" % dut.i_verilog.uart1.baud_gen_1.baud_freq.__class__.__name__)
        raise TestError()


@cocotb.test()
def recursive_discovery_boundary(dut):
    """
    Currently we can't traverse a language boundary during iteration

    However if we manually delve through the language boundary we
    should then be able to iterate to discover objects
    """
    tlog = logging.getLogger("cocotb.test")
    yield Timer(100)
    total = recursive_dump(dut.i_vhdl, tlog)
    tlog.info("Found a total of %d things", total)

