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

import cocotb
from cocotb.triggers import Timer

@cocotb.test()
def discover_module_values(dut):
    """Discover everything in the dut"""
    yield Timer(0)
    for thing in dut:
        thing.log.info("Found something: %s" % thing.fullname)

@cocotb.test(expect_error=True)
def discover_value_not_in_dut(dut):
    """Try and get a value from the DUT that is not there"""
    yield Timer(0)
    fake_signal = dut.fake_signal
    yield Timer(0)


@cocotb.test()
def access_signal(dut):
    """Access a signal using the assignment mechanism"""
    dut.stream_in_data = 1
    yield Timer(10)
    if dut.stream_in_data.value.integer != 1:
        raise TestError("%s.%s != %d" % (
           str(dut.stream_in_data.value.integer),
           dut.stream_in_data.value.integer))



@cocotb.test(expect_error=cocotb.SIM_NAME in ["Icarus Verilog"])
def access_single_bit(dut):
    """
    Access a single bit in a vector of the dut

    Icarus v0.96 doesn't support single bit access to vectors
    """
    dut.stream_in_data <= 0
    yield Timer(10)
    dut.log.info("%s = %d bits" % (str(dut.stream_in_data), len(dut.stream_in_data)))
    dut.stream_in_data[2] <= 1
    yield Timer(10)
    if dut.stream_out_data_comb.value.integer != (1<<2):
        raise TestError("%s.%s != %d" %
                (str(dut.stream_out_data_comb),
                dut.stream_out_data_comb.value.integer, (1<<2)))

@cocotb.test(expect_error=cocotb.SIM_NAME in ["Icarus Verilog"])
def access_single_bit_assignment(dut):
    """
    Access a single bit in a vector of the dut using the assignment mechanism

    Icarus v0.96 doesn't support single bit access to vectors
    """
    dut.stream_in_data = 0
    yield Timer(10)
    dut.log.info("%s = %d bits" % (str(dut.stream_in_data), len(dut.stream_in_data)))
    dut.stream_in_data[2] = 1
    yield Timer(10)
    if dut.stream_out_data_comb.value.integer != (1<<2):
        raise TestError("%s.%s != %d" %
                (str(dut.stream_out_data_comb),
                dut.stream_out_data_comb.value.integer, (1<<2)))

@cocotb.test(expect_error=True)
def access_single_bit_erroneous(dut):
    """Access a non-existent single bit"""
    yield Timer(10)
    dut.log.info("%s = %d bits" % (str(dut.stream_in_data), len(dut.stream_in_data)))
    bit = len(dut.stream_in_data) + 4
    dut.stream_in_data[bit] <= 1
    yield Timer(10)


@cocotb.test(skip=True)
def skip_a_test(dut):
    """This test shouldn't execute"""
    yield Timer(10)
    dut.log.info("%s = %d bits" % (str(dut.stream_in_data), len(dut.stream_in_data)))
    bit = len(dut.stream_in_data) + 4
    dut.stream_in_data[bit] <= 1
    yield Timer(10)
