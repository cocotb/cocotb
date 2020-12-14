'''
Copyright (c) 2013 Potential Ventures Ltd
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

import logging

import cocotb
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.clock import Clock
from cocotb.result import TestFailure

from cocotb_bus.drivers.avalon import AvalonMaster

import hal
import io_module


async def reset(dut, duration=10):
    dut._log.debug("Resetting DUT")
    dut.reset_n <= 0
    dut.stream_in_valid <= 0
    await Timer(duration, units='ns')
    await RisingEdge(dut.clk)
    dut.reset_n <= 1
    dut._log.debug("Out of reset")


@cocotb.test()
async def initial_hal_test(dut, debug=True):
    """Example of using the software HAL against cosim testbench"""

    cocotb.fork(Clock(dut.clk, 5, units='ns').start())
    await reset(dut)

    # Create the avalon master and direct our HAL calls to that
    master = AvalonMaster(dut, "csr", dut.clk)
    if debug:
        master.log.setLevel(logging.DEBUG)

    @cocotb.function
    async def read(address):
        master.log.debug("External source: reading address 0x%08X" % address)
        value = await master.read(address)
        master.log.debug("Reading complete: got value 0x%08x" % value)
        return value

    @cocotb.function
    async def write(address, value):
        master.log.debug("Write called for 0x%08X -> %d" % (address, value))
        await master.write(address, value)
        master.log.debug("Write complete")

    io_module.set_write_function(write)
    io_module.set_read_function(read)

    dut._log.info("READ/WRITE functions set up, initialising HAL")

    state = hal.endian_swapper_init(0)

    # Check the actual value
    if dut.byteswapping.value:
        raise TestFailure("Byteswapping is enabled but haven't configured DUT")

    await cocotb.external(hal.endian_swapper_enable)(state)

    await ReadOnly()

    if not dut.byteswapping.value:
        raise TestFailure("Byteswapping wasn't enabled after calling "
                          "endian_swapper_enable")

    dut._log.info("HAL call endian_swapper_enable successfully enabled the DUT")
