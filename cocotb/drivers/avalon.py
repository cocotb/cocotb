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
Drivers for Altera Avalon interfaces.

See http://www.altera.co.uk/literature/manual/mnl_avalon_spec.pdf

NB Currently we only support a very small subset of functionality
"""
from cocotb.decorators import coroutine
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.drivers import BusDriver, ValidatedBusDriver
from cocotb.utils import hexdump
from cocotb.binary import BinaryValue

class AvalonMM(BusDriver):
    """Avalon-MM Driver

    Currently we only support the mode required to communicate with SF avalon_mapper which
    is a limited subset of all the signals


    This needs some thought... do we do a transaction based mechanism or 'blocking' read/write calls?
    """
    _signals = ["readdata", "read", "write", "waitrequest", "writedata", "address"]

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)

        # Drive some sensible defaults
        self.bus.read           <= 0
        self.bus.write          <= 0


    def read(self, address):
        """
        """
        pass

    def write(self, address):
        """
        """
        pass


class AvalonST(ValidatedBusDriver):
    _signals = ["valid", "data"]


class AvalonSTPkts(ValidatedBusDriver):
    _signals = ["valid", "data", "startofpacket", "endofpacket", "empty"]
    _optional_signals = ["error", "channel", "ready"]

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
    def _send_string(self, string):
        """
        Args:
            string (str): A string of bytes to send over the bus
        """
        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)
        firstword = True

        # FIXME busses that aren't integer numbers of bytes
        bus_width = len(self.bus.data) / 8
        word = BinaryValue(bits=len(self.bus.data))


        # Drive some defaults since we don't know what state we're in
        self.bus.empty <= 0
        self.bus.startofpacket <= 0
        self.bus.endofpacket <= 0
        self.bus.error <= 0
        self.bus.valid <= 0


        while string:
            yield clkedge

            # Insert a gap where valid is low
            if not self.on:
                self.bus.valid <= 0
                for i in range(self.off):
                    yield clkedge
                self.on, self.off = self.valid_generator.next()

            # Consume a valid cycle
            if self.on is not True:
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
            word.buff = data[::-1]      # Big Endian FIXME
                

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
    def _send_iterable(self, pkt):
        """
        Args:
            pkt (iterable): Will yield objects with attributes matching the
                            signal names for each individual bus cycle
        """
        clkedge = RisingEdge(self.clock)

        for word in pkt:
            yield clkedge

            # Insert a gap where valid is low
            if not self.on:
                self.log.debug("Inserting %d non-valid cycles" % (self.off))
                self.bus.valid <= 0
                for i in range(self.off):
                    yield clkedge
                self.on, self.off = self.valid_generator.next()

            # Consume a valid cycle
            if self.on is not True:
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
    def _driver_send(self, pkt):
        """Send a packet over the bus

        Args:
            pkt (str or iterable): packet to drive onto the bus

        If pkt is a string, we simply send it word by word

        If pkt is an iterable, it's assumed to yield objects with attributes
        matching the signal names
        """

        # Avoid spurious object creation by recycling

        self.log.info("Sending packet of length %d bytes" % len(pkt))
        self.log.debug(hexdump(pkt))

        if isinstance(pkt, str):
            yield self._send_string(pkt)
        else:
            yield self._send_iterable(pkt)

        self.log.info("Packet sent successfully")
