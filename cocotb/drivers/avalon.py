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
"""
Drivers for Altera Avalon interfaces.

See http://www.altera.co.uk/literature/manual/mnl_avalon_spec.pdf

NB Currently we only support a very small subset of functionality
"""
from cocotb.decorators import coroutine
from cocotb.triggers import RisingEdge, ReadOnly, NextTimeStep, Event
from cocotb.drivers import BusDriver, ValidatedBusDriver
from cocotb.utils import hexdump
from cocotb.binary import BinaryValue
from cocotb.result import ReturnValue


class AvalonMM(BusDriver):
    """Avalon-MM Driver

    Currently we only support the mode required to communicate with SF avalon_mapper which
    is a limited subset of all the signals

    Blocking operation is all that is supported at the moment, and for the near future as well
    Posted responses from a slave are not supported.
    """
    _signals = ["readdata", "read", "write", "waitrequest", "writedata", "address"]

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)

        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.read.setimmediatevalue(0)
        self.bus.write.setimmediatevalue(0)
        self.bus.address.setimmediatevalue(0)

    def read(self, address):
        pass


    def write(self, address, value):
        pass

class AvalonMaster(AvalonMM):
    """Avalon-MM master
    """
    def __init__(self, entity, name, clock):
        AvalonMM.__init__(self, entity, name, clock)
        self.log.debug("AvalonMaster created")
        self.busy_event = Event("%s_busy" % name)
        self.busy = False

    @coroutine
    def _acquire_lock(self):
        if self.busy:
            yield self.busy_event.wait()
        self.busy_event.clear()
        self.busy = True

    def _release_lock(self):
        self.busy = False
        self.busy_event.set()

    @coroutine
    def read(self, address):
        """
        Issue a request to the bus and block until this
        comes back. Simulation time still progresses
        but syntactically it blocks.
        See http://www.altera.com/literature/manual/mnl_avalon_spec_1_3.pdf
        """
        yield self._acquire_lock()

        # Apply values for next clock edge
        yield RisingEdge(self.clock)
        self.bus.address <= address
        self.bus.read <= 1

        # Wait for waitrequest to be low
        yield self._wait_for_nsignal(self.bus.waitrequest)

        # Assume readLatency = 1
        # FIXME need to configure this, should take a dictionary of Avalon properties.
        yield RisingEdge(self.clock)

        # Deassert read
        self.bus.read <= 0

        # Get the data
        yield ReadOnly()
        data = self.bus.readdata.value
        yield NextTimeStep()
        self._release_lock()
        raise ReturnValue(data)

    @coroutine
    def write(self, address, value):
        """
        Issue a write to the given address with the specified
        value.
        See http://www.altera.com/literature/manual/mnl_avalon_spec_1_3.pdf
        """
        yield self._acquire_lock()

        # Apply valuse to bus
        yield RisingEdge(self.clock)
        self.bus.address <= address
        self.bus.writedata <= value
        self.bus.write <= 1

        # Wait for waitrequest to be low
        count = yield self._wait_for_nsignal(self.bus.waitrequest)

        # Deassert write
        yield RisingEdge(self.clock)
        self.bus.write <= 0
        self._release_lock()


class AvalonSlave(AvalonMM):
    """Avalon-MM Slave

    This is not supported at the moment
    """
    def __init__(self, entity, name, clock):
        AvalonMM.__init__(self, entity, name, clock)


class AvalonST(ValidatedBusDriver):
    _signals = ["valid", "data"]


class AvalonSTPkts(ValidatedBusDriver):
    _signals = ["valid", "data", "startofpacket", "endofpacket", "empty"]
    _optional_signals = ["error", "channel", "ready"]

    _default_config = {
        "dataBitsPerSymbol"             : 8,
        "firstSymbolInHighOrderBits"    : True,
        "maxChannel"                    : 0,
        "readyLatency"                  : 0
    }

    def __init__(self, *args, **kwargs):
        config = kwargs.pop('config', {})
        ValidatedBusDriver.__init__(self, *args, **kwargs)

        self.config = AvalonSTPkts._default_config.copy()

        for configoption, value in config.iteritems():
            self.config[configoption] = value
            self.log.debug("Setting config option %s to %s" % (configoption, str(value)))

    @coroutine
    def _wait_ready(self):
        """Wait for a ready cycle on the bus before continuing

            Can no longer drive values this cycle...

            FIXME assumes readyLatency of 0
        """
        yield ReadOnly()
        while not self.bus.ready.value:
            yield RisingEdge(self.clock)
            yield ReadOnly()

    @coroutine
    def _send_string(self, string, sync=True):
        """
        Args:
            string (str): A string of bytes to send over the bus
        """
        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        firstword = True

        # FIXME busses that aren't integer numbers of bytes
        bus_width = len(self.bus.data) / 8

        word = BinaryValue(bits=len(self.bus.data), bigEndian=self.config['firstSymbolInHighOrderBits'])

        # Drive some defaults since we don't know what state we're in
        self.bus.empty <= 0
        self.bus.startofpacket <= 0
        self.bus.endofpacket <= 0
        self.bus.valid <= 0
        if hasattr(self.bus, 'error'):
            self.bus.error <= 0

        while string:
            if not firstword or (firstword and sync):
                yield clkedge

            # Insert a gap where valid is low
            if not self.on:
                self.bus.valid <= 0
                for i in range(self.off):
                    yield clkedge

                # Grab the next set of on/off values
                self._next_valids()

            # Consume a valid cycle
            if self.on is not True and self.on:
                self.on -= 1

            self.bus.valid <= 1

            if firstword:
                self.bus.empty <= 0
                self.bus.startofpacket <= 1
                firstword = False
            else:
                self.bus.startofpacket <= 0

            nbytes = min(len(string), bus_width)
            data = string[:nbytes]
            word.buff = data

            if len(string) <= bus_width:
                self.bus.endofpacket <= 1
                self.bus.empty <= bus_width - len(string)
                string = ""
            else:
                string = string[bus_width:]

            self.bus.data <= word

            # If this is a bus with a ready signal, wait for this word to
            # be acknowledged
            if hasattr(self.bus, "ready"):
                yield self._wait_ready()

        yield clkedge
        self.bus.valid <= 0
        self.bus.endofpacket <= 0


    @coroutine
    def _send_iterable(self, pkt, sync=True):
        """
        Args:
            pkt (iterable): Will yield objects with attributes matching the
                            signal names for each individual bus cycle
        """
        clkedge = RisingEdge(self.clock)
        firstword = True

        for word in pkt:
            if not firstword or (firstword and sync):
                yield clkedge

            firstword = False

            # Insert a gap where valid is low
            if not self.on:
                self.bus.valid <= 0
                for i in range(self.off):
                    yield clkedge

                # Grab the next set of on/off values
                self._next_valids()

            # Consume a valid cycle
            if self.on is not True and self.on:
                self.on -= 1

            self.bus <= word
            self.bus.valid <= 1

            # If this is a bus with a ready signal, wait for this word to
            # be acknowledged
            if hasattr(self.bus, "ready"):
                yield self._wait_ready()

        yield clkedge
        self.bus.valid <= 0

    @coroutine
    def _driver_send(self, pkt, sync=True):
        """Send a packet over the bus

        Args:
            pkt (str or iterable): packet to drive onto the bus

        If pkt is a string, we simply send it word by word

        If pkt is an iterable, it's assumed to yield objects with attributes
        matching the signal names
        """

        # Avoid spurious object creation by recycling

        self.log.debug("Sending packet of length %d bytes" % len(pkt))
        self.log.debug(hexdump(pkt))

        if isinstance(pkt, str):
            yield self._send_string(pkt, sync=sync)
        else:
            yield self._send_iterable(pkt, sync=sync)

        self.log.info("Sucessfully sent packet of length %d bytes" % (len(pkt)))

