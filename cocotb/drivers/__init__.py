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
from cocotb.triggers import Event, RisingEdge, ReadOnly
from cocotb.bus import Bus
from cocotb.log import SimLog
from cocotb.result import ReturnValue


class BitDriver(object):
    """
    Drives a signal onto a single bit

    Useful for exercising ready / valid
    """
    def __init__(self, signal, clk, generator=None):
        self._signal = signal
        self._clk = clk
        self._generator = generator

    def start(self, generator=None):
        self._cr = cocotb.fork(self._cr_twiddler(generator=generator))

    def stop(self):
        self._cr.kill()

    @cocotb.coroutine
    def _cr_twiddler(self, generator=None):
        if generator is None and self._generator is None:
            raise Exception("No generator provided!")
        if generator is not None:
            self._generator = generator

        edge = RisingEdge(self._clk)

        # Actual thread
        while True:
            on,off = self._generator.next()
            self._signal <= 1
            for i in range(on):
                yield edge
            self._signal <= 0
            for i in range(off):
                yield edge

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
            self.log = SimLog("cocotb.driver.%s" % (self.__class__.__name__))

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
    """
    Wrapper around common functionality for busses which have:
        a list of _signals (class attribute)
        a list of _optional_signals (class attribute)
        a clock
        a name
        an entity
    """
    _optional_signals = []

    def __init__(self, entity, name, clock):
        """
        Args:
            entity (SimHandle) : a handle to the simulator entity

            name (str) : name of this bus

            clock (SimHandle) : A handle to the clock associated with this bus
        """
        self.log = SimLog("cocotb.%s.%s" % (entity.name, name))
        Driver.__init__(self)
        self.entity = entity
        self.name = name
        self.clock = clock
        self.bus = Bus(self.entity, self.name, self._signals, self._optional_signals)


    @coroutine
    def _driver_send(self, transaction):
        yield RisingEdge(self.clock)
        self.bus <= transaction

    @coroutine
    def __wait_for_value_on_signal(self, signal, level):
        loops = 0
        yield ReadOnly()
        while not signal.value is not level:
            yield RisingEdge(self.clock)
            yield ReadOnly()
            loops += 1

        raise ReturnValue(loops)

    @coroutine
    def _wait_for_signal(self, signal):
        """This method will return with the specified signal
        has hit logic 1. The state will be in the ReadOnly phase
        so sim will need to move to NextTimeStep before
        registering more callbacks can occour
        """
        res = yield self.__wait_for_value_on_signal(signal, 1)

        raise ReturnValue(res)

    @coroutine
    def _wait_for_nsignal(self, signal):
        """This method will return with the specified signal
        has hit logic 0. The state will be in the ReadOnly phase
        so sim will need to move to NextTimeStep before
        registering more callbacks can occour
        """
        res = yield self.__wait_for_value_on_signal(signal, 0)

        raise ReturnValue(res)


class ValidatedBusDriver(BusDriver):
    """
    Same as a BusDriver except we support an optional generator to control
    which cycles are valid
    """

    def __init__(self, entity, name, clock, valid_generator=None):
        """
        Args:
            entity (SimHandle) : a handle to the simulator entity

            name (str) : name of this bus

            clock (SimHandle) : A handle to the clock associated with this bus
        Kwargs:
            valid_generator (generator): a generator that yields tuples  of
                                        (valid, invalid) cycles to insert
        """
        BusDriver.__init__(self, entity, name, clock)
        self.set_valid_generator(valid_generator=valid_generator)


    def set_valid_generator(self, valid_generator=None):
        """
        Set a new valid generator for this bus
        """

        self.valid_generator = valid_generator

        # Optionally insert invalid cycles every N
        if self.valid_generator is not None:
            self.on, self.off = valid_generator.next()
            self.log.debug("Will be on for %d cycles, off for %s" % (self.on, self.off))
        else:
            # Valid every clock cycle
            self.on, self.off = True, False
            self.log.debug("Not using valid generator")
