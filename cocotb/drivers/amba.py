''' Copyright (c) 2014 Potential Ventures Ltd
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
Drivers for Advanced Microcontroller Bus Architecture
"""
import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Lock
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue


class AXIReadError(Exception): pass


class AXI4LiteMaster(BusDriver):
    """
    AXI4-Lite Master

    TODO: Kill all pending transactions if reset is asserted...
    """
    _signals = ["ARESETn",
                "AWVALID", "AWADDR", "AWREADY",         # Write address channel
                "WVALID", "WREADY", "WDATA", "WSTRB",   # Write data channel
                "BVALID", "BREADY", "BRESP",            # Write response channel
                "ARVALID", "ARADDR", "ARREADY",         # Read address channel
                "RVALID", "RREADY", "RRESP", "RDATA"]   # Read data channel

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)

        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.AWVALID.setimmediatevalue(0)
        self.bus.WVALID.setimmediatevalue(0)
        self.bus.ARVALID.setimmediatevalue(0)
        self.bus.BREADY.setimmediatevalue(1)
        self.bus.RREADY.setimmediatevalue(1)

        # Mutex for each channel that we master to prevent contention
        self.write_address_busy = Lock("%s_wabusy" % name)
        self.read_address_busy = Lock("%s_rabusy" % name)
        self.write_data_busy = Lock("%s_wbusy" % name)


    @cocotb.coroutine
    def _send_write_address(self, address, delay=0):
        """
        Send the write address, with optional delay
        """
        yield self.write_address_busy.acquire()
        for cycle in xrange(delay):
            yield RisingEdge(self.clock)

        self.bus.AWADDR         <= address
        self.bus.AWVALID        <= 1

        while True:
            yield ReadOnly()
            if self.bus.AWREADY.value:
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.AWVALID        <= 0
        self.write_address_busy.release()

    @cocotb.coroutine
    def _send_write_data(self, data, delay=0, byte_enable=0xF):
        """
        Send the write address, with optional delay
        """
        yield self.write_data_busy.acquire()
        for cycle in xrange(delay):
            yield RisingEdge(self.clock)

        self.bus.WDATA          <= data
        self.bus.WVALID         <= 1
        self.bus.WSTRB          <= byte_enable

        while True:
            yield ReadOnly()
            if self.bus.WREADY.value:
                break
            yield RisingEdge(self.clock)
        yield RisingEdge(self.clock)
        self.bus.WVALID        <= 0
        self.write_data_busy.release()


    @cocotb.coroutine
    def write(self, address, value, byte_enable=0xf, address_latency=0, data_latency=0):
        """
        Write a value to an address.

        The *_latency KWargs allow control over the delta 
        """
        c_addr = cocotb.fork(self._send_write_address(address, delay=address_latency))
        c_data = cocotb.fork(self._send_write_data(value, byte_enable=byte_enable, delay=data_latency))

        if c_addr:
            yield c_addr.join()
        if c_data:
            yield c_data.join()

        # Wait for the response
        while True:
            yield ReadOnly()
            if self.bus.BVALID.value and self.bus.BREADY.value:
                result = self.bus.BRESP.value
                break
            yield RisingEdge(self.clock)

        if int(result):
            raise AXIReadError("Write to address 0x%08x failed with BRESP: %d" %(
                address, int(result)))

        raise ReturnValue(result)


    @cocotb.coroutine
    def read(self, address, sync=True):
        """
        Read from an address.
        """
        if sync:
            yield RisingEdge(self.clock)

        self.bus.ARADDR         <= address
        self.bus.ARVALID        <= 1

        while True:
            yield ReadOnly()
            if self.bus.WREADY.value:
                break
            yield RisingEdge(self.clock)

        yield RisingEdge(self.clock)
        self.bus.ARVALID        <= 0

        while True:
            yield ReadOnly()
            if self.bus.RVALID.value and self.bus.RREADY.value:
                data = self.bus.RDATA.value
                result = self.bus.RRESP.value
                break
            yield RisingEdge(self.clock)

        if int(result):
            raise AXIReadError("Read address 0x%08x failed with RRESP: %d" %(
                address, int(result)))

        raise ReturnValue(data)
