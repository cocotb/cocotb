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
    Set of common driver base classes
"""


import logging

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Event
from cocotb.bus import Bus

class Driver(object):
    """

    Class defining the standard interface for a driver within a testbench

    The driver is responsible for serialising transactions onto the physical pins
    of the interface.  This may consume simulation time.
    """
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
        try:
            while True:

                # Sleep until we have something to send
                while not self._sendQ:
                    yield self._pending.wait()

                transaction, callback, event = self._sendQ.pop(0)
                # Send the pending transaction
                self.log.info("Sending packet...")
                yield self._send(transaction, callback, event)
                self.log.info("Done, shouldn't be waiting on _send.join() anymore..")
        except StopIteration:
            self.log.info("Stopping send thread on driver")


class BusDriver(Driver):
    """
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

class ValidatedBusDriver(BusDriver):
    """


    """


    
