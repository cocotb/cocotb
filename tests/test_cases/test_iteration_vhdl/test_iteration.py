''' Copyright (c) 2015, 2018 Potential Ventures Ltd
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
from cocotb.result import TestFailure

@cocotb.test()
def recursive_discovery(dut):
    """
    Recursively discover every single object in the design
    """
    if (cocotb.SIM_NAME.lower().startswith(("ncsim", "xmsim", "modelsim")) or
        (cocotb.SIM_NAME.lower().startswith("riviera") and not cocotb.SIM_VERSION.startswith("2016.02"))):
        # Finds regions, signal, generics, constants, varibles and ports.
        pass_total = 34569
    else:
        pass_total = 32393

    tlog = logging.getLogger("cocotb.test")
    yield Timer(100)
    def dump_all_the_things(parent):
        count = 0
        for thing in parent:
            count += 1
            tlog.info("Found %s.%s (%s)", parent._name, thing._name, type(thing))
            count += dump_all_the_things(thing)
        return count
    total = dump_all_the_things(dut)
    tlog.info("Found a total of %d things", total)
    if total != pass_total:
        raise TestFailure("Expected %d objects but found %d" % (pass_total, total))


@cocotb.test()
def discovery_all(dut):
    dut._log.info("Trying to discover")
    yield Timer(0)
    for thing in dut:
        thing._log.info("Found something: %s", thing._fullname)
        #for subthing in thing:
        #    thing._log.info("Found something: %s" % thing._fullname)

    dut._log.info("length of dut.inst_acs is %d", len(dut.gen_acs))
    item = dut.gen_acs[3]
    item._log.info("this is item")

@cocotb.coroutine
def iteration_loop(dut):
    for thing in dut:
        thing._log.info("Found something: %s", thing._fullname)
        yield Timer(1)

@cocotb.test()
def dual_iteration(dut):
    loop_one = cocotb.fork(iteration_loop(dut))
    loop_two = cocotb.fork(iteration_loop(dut))

    yield [loop_one.join(), loop_two.join()]

@cocotb.test()
def get_clock(dut):
    dut._log.info("dut.aclk is %s", dut.aclk.__class__.__name__)
    dut.aclk <= 0
    yield Timer(1)
    dut.aclk <= 1
    yield Timer(1)
    if int(dut.aclk) is not 1:
        raise TestFailure("dut.aclk is not what we expected (got %d)" % int(dut.aclk))

@cocotb.test()
def test_n_dimension_array(dut):
    tlog = logging.getLogger("cocotb.test")
    inner_count = 0
    outer_count = 0
    yield Timer(0)
    config = dut.inst_ram_ctrl.config
    # This signal is a 2 x 7 vhpiEnumVecVal
    for thing in config:
        for sub_thing in thing:
            tlog.info("Found %s", sub_thing._name)
            inner_count += 1
        outer_count += 1

    if inner_count != 14 or outer_count != 2:
        raise TestFailure("dut.inst_ram_ctrl.config should have a total of 14 elems over 2 loops")
