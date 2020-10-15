#!/usr/bin/env python

# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
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

import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.clock import Clock


async def test_read(dut):
    global test_count
    dut._log.info("Inside test_read")
    while test_count != 5:
        await RisingEdge(dut.clk)
        test_count += 1


async def run_external(dut):
    await cocotb.external(test_read)(dut)


async def clock_mon(dut):
    await RisingEdge(dut.clk)


@cocotb.test(
    expect_fail=True,
    skip=cocotb.SIM_NAME.lower().startswith("riviera"),  # gh-1859
    expect_error=cocotb.SIM_NAME.lower().startswith("modelsim")  # $fatal() fails hard on Questa
)
async def test_failure_from_system_task(dut):
    """
    Allow the dut to call system tasks from verilog.
    $fatal() will fail the test, and scheduler will cleanup forked coroutines.
    """
    cocotb.fork(Clock(dut.clk, 100, units='ns').start())
    cocotb.fork(clock_mon(dut))
    cocotb.fork(run_external(dut))
    await Timer(10000000, units='ns')


@cocotb.test(skip=cocotb.SIM_NAME.lower().startswith("riviera"))  # gh-1859
async def test_after_system_task_fail(dut):
    """
    Test to run after failed test.
    """
    await Timer(1, units='ns')
