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
A set of tests that demonstrate cocotb functionality

Also used a regression test of cocotb capabilities
"""

import cocotb
from cocotb.triggers import Timer




# Tests relating to providing meaningful errors if we forget to use the
# yield keyword correctly to turn a function into a coroutine

@cocotb.test(expect_fail=True)
def test_not_a_coroutine(dut):
    """Example of a failing to use the yield keyword in a test"""
    dut.log.warning("This test will fail because we don't yield anything")

@cocotb.coroutine
def function_not_a_coroutine():
    """If we don't yield, this isn't a coroutine"""
    return "This should fail"

@cocotb.test(expect_fail=True)
def test_function_not_a_coroutine(dut):
    """Example of trying to yield a coroutine that isn't a coroutine"""
    yield Timer(500)
    yield function_not_a_coroutine()

@cocotb.test(expect_fail=True)
def test_function_not_a_coroutine_fork(dut):
    """Example of trying to fork a coroutine that isn't a coroutine"""
    yield Timer(500)
    cocotb.fork(function_not_a_coroutine())
    yield Timer(500)

@cocotb.coroutine
def clock_gen(clock):
    """Example clock gen for test use"""
    for i in range(5):
        clock <= 0
        yield Timer(100)
        clock <= 1
        yield Timer(100)
    clock.log.warning("Clock generator finished!") 

@cocotb.test(expect_fail=False)
def test_yield_list(dut):
    """Example of yeilding on a list of triggers"""
    clock = dut.clk;
    cocotb.scheduler.add(clock_gen(clock))
    yield [Timer(5000), Timer(6000)]

    yield Timer(10000)

@cocotb.test(expect_fail=True)
def test_duplicate_yield(dut):
    """A trigger can not be yielded on twice"""
