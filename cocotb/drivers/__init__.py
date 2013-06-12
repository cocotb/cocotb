#!/bin/env python

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

    Class defining the standard interface for a driver within a testbench

    The driver is responsible for serialising transactions onto the physical pins
    of the interface.  This may consume simulation time.

"""

import logging
import math

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Edge, Event, RisingEdge
from cocotb.bus import Bus

class Driver(object):


    def __init__(self):
        """
        Constructor for a driver instance
        """
        #self._busy = Lock()
        self._pending = Event(name="Driver._pending")
        self._sendQ = []

        # Subclasses may already set up logging
        if not hasattr(self, "log"):
            self.log = logging.getLogger("cocotb.driver.%s" % (self.__class__.__name__))

        # Create an independent coroutine which can send stuff
        self._thread = cocotb.scheduler.add(self._send_thread())


    def kill(self):
        if self._thread:
            self._thread.kill()
            self._thread = None

    def append(self, transaction, callback=None, event=None):
        """
        Queue up a transaction to be sent over the bus.

        Mechanisms are provided to permit the caller to know when the transaction is processed

        callback: optional function to be called when the transaction has been sent

        event: event to be set when the tansaction has been sent
        """
        self._sendQ.append((transaction, callback, event))
        self._pending.set()

    @coroutine
    def send(self, transaction):
        """
        Blocking send call (hence must be "yielded" rather than called)

        Sends the transaction over the bus
        """
        #yield self.busy.acquire()
        yield self._send(transaction, None, None)


    def _driver_send(self, transaction):
        """
        actual impementation of the send.

        subclasses should override this method to implement the actual send routine
        """
        pass


    @coroutine
    def _send(self, transaction, callback, event):
        """
        assumes the caller has already acquired the busy lock

        releases busy lock once sending is complete
        """
        yield self._driver_send(transaction)

        # Notify the world that this transaction is complete
        if event:       event.set()
        if callback:    callback(transaction)

        # No longer hogging the bus
        #self.busy.release()

    @coroutine
    def _send_thread(self):
        while True:

            # Sleep until we have something to send
            while not self._sendQ:
                yield self._pending.wait()

            transaction, callback, event = self._sendQ.pop(0)
            # Send the pending transaction
            self.log.info("Sending packet...")
            yield self._send(transaction, callback, event)
            self.log.info("Done, shouldn't be waiting on _send.join() anymore..")


class BusDriver(Driver):
    """Tickets please!

    Wrapper around common functionality for busses which have:
        a list of _signals (class attribute)
        a clock
        a name
        an entity
    """

    def __init__(self, entity, name, clock):
        self.log = logging.getLogger("cocotb.%s.%s" % (entity.name, name))
        Driver.__init__(self)
        self.entity = entity
        self.name = name
        self.clock = clock
        self.bus = Bus(self.entity, self.name, self._signals)


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




class AvalonST(Driver):
    _signals = ["valid", "data"]

class SFStreaming(BusDriver):
    """This is the Solarflare Streaming bus as defined by the FDK.

    Expect to see a 72-bit bus (bottom 64 bits data, top 8 bits are ECC)
    """
    _signals = AvalonST._signals + ["startofpacket", "endofpacket", "ready", "empty", "channel", "error"]

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)

        # Drive some sensible defaults onto the bus
        self.bus.startofpacket <= 0
        self.bus.endofpacket   <= 0
        self.bus.valid         <= 0
        self.bus.empty         <= 0
        self.bus.channel       <= 0
        self.bus.error         <= 0

    @coroutine
    def _driver_send(self, sfpkt):
        """Send a packet over the bus

            sfpkt should be an instance of SFStreamingPacket
        """
        # Avoid spurious object creation by recycling
        clkedge = RisingEdge(self.clock)

        self.log.info("Sending packet of length %d bytes" % len(sfpkt))

        for word in sfpkt:
            yield clkedge
            while self.bus.ready != 1:
                yield clkedge
            self.bus.drive(word)

        yield clkedge
        self.bus.endofpacket <= 0
        self.bus.valid <= 0

        self.log.info("Packet sent successfully")
