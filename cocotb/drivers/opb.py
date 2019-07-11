# Copyright (c) 2015 Potential Ventures Ltd
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

"""
Drivers for On-chip Peripheral Bus.

NOTE: Currently we only support a very small subset of functionality.
"""

import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Event
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue


class OPBException(Exception):
    pass


class OPBMaster(BusDriver):
    """On-chip peripheral bus master."""
    _signals = ["xferAck", "errAck", "toutSup", "retry", "DBus_out", "select",
                "RNW", "BE", "ABus", "DBus_in"]
    _optional_signals = ["seqAddr"]
    _max_cycles = 16

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)
        self.bus.select.setimmediatevalue(0)
        self.log.debug("OPBMaster created")
        self.busy_event = Event("%s_busy" % name)
        self.busy = False

    @cocotb.coroutine
    def _acquire_lock(self):
        if self.busy:
            yield self.busy_event.wait()
        self.busy_event.clear()
        self.busy = True

    def _release_lock(self):
        self.busy = False
        self.busy_event.set()

    @cocotb.coroutine
    def read(self, address, sync=True):
        """Issue a request to the bus and block until this comes back.

        Simulation time still progresses but syntactically it blocks.
        
        Args:
            address (int): The address to read from.
            sync (bool, optional): Wait for rising edge on clock initially.
                Defaults to True.
            
        Returns:
            BinaryValue: The read data value.
            
        Raises:
            OPBException: If read took longer than 16 cycles.
        """
        yield self._acquire_lock()

        # Apply values for next clock edge
        if sync:
            yield RisingEdge(self.clock)
        self.bus.ABus <= address
        self.bus.select <= 1
        self.bus.RNW <= 1
        self.bus.BE <= 0xF

        count = 0
        while not int(self.bus.xferAck.value):
            yield RisingEdge(self.clock)
            yield ReadOnly()
            if int(self.bus.toutSup.value):
                count = 0
            else:
                count += 1
            if count >= self._max_cycles:
                raise OPBException("Read took longer than 16 cycles")
        data = int(self.bus.DBus_out.value)

        # Deassert read
        self.bus.select <= 0
        self._release_lock()
        self.log.info("Read of address 0x%x returned 0x%08x" % (address, data))
        raise ReturnValue(data)

    @cocotb.coroutine
    def write(self, address, value, sync=True):
        """Issue a write to the given address with the specified value.
        
        Args:
            address (int): The address to read from.
            value (int): The data value to write.
            sync (bool, optional): Wait for rising edge on clock initially.
                Defaults to True.
            
        Raises:
            OPBException: If write took longer than 16 cycles.
        """
        yield self._acquire_lock()

        if sync:
            yield RisingEdge(self.clock)
        self.bus.ABus <= address
        self.bus.select <= 1
        self.bus.RNW <= 0
        self.bus.BE <= 0xF
        self.bus.DBus_out <= value

        count = 0
        while not int(self.bus.xferAck.value):
            yield RisingEdge(self.clock)
            yield ReadOnly()
            if int(self.bus.toutSup.value):
                count = 0
            else:
                count += 1
            if count >= self._max_cycles:
                raise OPBException("Write took longer than 16 cycles")

        self.bus.select <= 0
        self._release_lock()
