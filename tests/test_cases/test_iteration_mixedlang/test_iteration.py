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


@cocotb.test(expect_fail=True)
def test_drivers(dut):
    """
    Try iterating over drivers of a signal.

    Seems that few simulators implement vpiDriver
    """
    tlog = logging.getLogger("cocotb.test")
    yield Timer(100)
    for driver in dut.i_verilog.uart1.uart_rx_1.rx_data.drivers():
        tlog.info("Found %s" % repr(driver))
        break
    else:
        raise TestFailure("No drivers found for dut.i_verilog.uart1.uart_rx_1.rx_data")


@cocotb.test()
def recursive_discovery(dut):
    """
    Recursively discover every single object in the design
    """
    if cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim")):
        # vpiAlways = 31 and vpiStructVar = 2 do not show up in IUS/Xcelium
        pass_total = 917
    elif cocotb.SIM_NAME.lower().startswith(("modelsim")):
        pass_total = 933
    else:
        pass_total = 966

    tlog = logging.getLogger("cocotb.test")
    yield Timer(100)
    total = recursive_dump(dut, tlog)

    if pass_total != total:
        raise TestFailure("Expected %d but found %d" % (pass_total, total))
    else:
        tlog.info("Found a total of %d things", total)

    if not isinstance(dut.i_verilog.uart1.baud_gen_1.baud_freq, cocotb.handle.ModifiableObject):
        tlog.error("Expected dut.i_verilog.uart1.baud_gen_1.baud_freq to be modifiable")
        tlog.error("but it was %s" % dut.i_verilog.uart1.baud_gen_1.baud_freq.__class__.__name__)
        raise TestFailure()


@cocotb.test()
def recursive_discovery_boundary(dut):
    """
    Iteration though the boundary works but this just double checks
    """
    if cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim")):
        pass_total = 462
    else:
        pass_total = 478

    tlog = logging.getLogger("cocotb.test")
    yield Timer(100)
    total = recursive_dump(dut.i_vhdl, tlog)
    tlog.info("Found a total of %d things", total)
    if total != pass_total:
        raise TestFailure("Expected %d objects but found %d" % (pass_total, total))

