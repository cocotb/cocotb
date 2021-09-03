# Copyright (c) 2015, 2018 Potential Ventures Ltd
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging

import cocotb
from cocotb.triggers import First


@cocotb.test(expect_fail=cocotb.SIM_NAME in ["Icarus Verilog"])
async def recursive_discovery(dut):
    """
    Recursively discover every single object in the design
    """
    if cocotb.SIM_NAME.lower().startswith(("modelsim",
                                           "ncsim",
                                           "xmsim",
                                           "chronologic simulation vcs")):
        # vpiAlways does not show up
        pass_total = 259
    else:
        pass_total = 265

    tlog = logging.getLogger("cocotb.test")

    def dump_all_the_things(parent):
        count = 0
        for thing in parent:
            count += 1
            tlog.info("Found %s.%s (%s)", parent._name, thing._name, type(thing))
            count += dump_all_the_things(thing)
        return count
    total = dump_all_the_things(dut)
    tlog.info("Found a total of %d things", total)
    assert total == pass_total


async def iteration_loop(dut):
    for thing in dut:
        thing._log.info("Found something: %s" % thing._fullname)


@cocotb.test()
async def dual_iteration(dut):
    loop_one = cocotb.start_soon(iteration_loop(dut))
    loop_two = cocotb.start_soon(iteration_loop(dut))

    await First(loop_one.join(), loop_two.join())
