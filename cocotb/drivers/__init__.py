#!/bin/env python

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
    Set of common driver base classes
"""

import logging
from collections import deque

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import (Event, RisingEdge, ReadOnly, Timer, NextTimeStep,
                             Edge)
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
            on, off = next(self._generator)
            self._signal <= 1
            for i in range(on):
                yield edge
            self._signal <= 0
            for i in range(off):
                yield edge


class Driver(object):
    """

    Class defining the standard interface for a driver within a testbench

    The driver is responsible for serialising transactions onto the physical
    pins of the interface.  This may consume simulation time.
    """
    def __init__(self):
        """
        Constructor for a driver instance
        """
        # self._busy = Lock()
        self._pending = Event(name="Driver._pending")
        self._sendQ = deque()

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

        Mechanisms are provided to permit the caller to know when the
        transaction is processed

        callback: optional function to be called when the transaction has been
        sent

        event: event to be set when the tansaction has been sent
        """
        self._sendQ.append((transaction, callback, event))
        self._pending.set()

    def clear(self):
        """
        Clear any queued transactions without sending them onto the bus
        """
        self._sendQ = deque()

    @coroutine
    def send(self, transaction, sync=True):
        """
        Blocking send call (hence must be "yielded" rather than called)

        Sends the transaction over the bus

        Args:
            transaction (any): the transaction to send

        Kwargs:
            sync (boolean): synchronise the transfer by waiting for risingedge
        """
        yield self._send(transaction, None, None, sync=sync)

    def _driver_send(self, transaction, sync=True):
        """
        actual impementation of the send.

        subclasses should override this method to implement the actual send
        routine
        """
        raise NotImplementedError("Subclasses of Driver should define a "
                                  "_driver_send coroutine")

    @coroutine
    def _send(self, transaction, callback, event, sync=True):
        """
        assumes the caller has already acquired the busy lock

        releases busy lock once sending is complete
        """
        yield self._driver_send(transaction, sync=sync)

        # Notify the world that this transaction is complete
        if event:
            event.set()
        if callback:
            callback(transaction)

        # No longer hogging the bus
        # self.busy.release()

    @coroutine
    def _send_thread(self):
        while True:

            # Sleep until we have something to send
            while not self._sendQ:
                self._pending.clear()
                yield self._pending.wait()

            synchronised = False

            # Send in all the queued packets,
            # only synchronise on the first send
            while self._sendQ:
                transaction, callback, event = self._sendQ.popleft()
                self.log.debug("Sending queued packet...")
                yield self._send(transaction, callback, event,
                                 sync=not synchronised)
                synchronised = True


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

    def __init__(self, entity, name, clock, **kwargs):
        """
        Args:
            entity (SimHandle) : a handle to the simulator entity

            name (str) : name of this bus. None for nameless bus, e.g.
                         bus-signals in an interface or a modport
                         (untested on struct/record,
                          but could work here as well)
            clock (SimHandle) : A handle to the clock associated with this bus
        """
        self.log = SimLog("cocotb.%s.%s" % (entity._name, name))
        Driver.__init__(self)
        self.entity = entity
        self.name = name
        self.clock = clock
        self.bus = Bus(self.entity, self.name, self._signals,
                       self._optional_signals, array_idx=kwargs.get("array_idx"))

    @coroutine
    def _driver_send(self, transaction, sync=True):
        if sync:
            yield RisingEdge(self.clock)
        self.bus <= transaction

    @coroutine
    def _wait_for_signal(self, signal):
        """This method will return with the specified signal
        has hit logic 1. The state will be in the ReadOnly phase
        so sim will need to move to NextTimeStep before
        registering more callbacks can occour
        """
        yield ReadOnly()
        while signal.value.integer != 1:
            yield RisingEdge(signal)
            yield ReadOnly()
        yield NextTimeStep()

    @coroutine
    def _wait_for_nsignal(self, signal):
        """This method will return with the specified signal
        has hit logic 0. The state will be in the ReadOnly phase
        so sim will need to move to NextTimeStep before
        registering more callbacks can occour
        """
        yield ReadOnly()
        while signal.value.integer != 0:
            yield Edge(signal)
            yield ReadOnly()
        yield NextTimeStep()

    def __str__(self):
        """Provide the name of the bus"""
        return str(self.name)


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

    def _next_valids(self):
        """
        Optionally insert invalid cycles every N cycles
        Generator should return a tuple with the number of cycles to be
        on followed by the number of cycles to be off.
        The 'on' cycles should be non-zero, we skip invalid generator entries
        """
        self.on = False

        if self.valid_generator is not None:
            while not self.on:
                try:
                    self.on, self.off = next(self.valid_generator)
                except StopIteration:
                    # If the generator runs out stop inserting non-valid cycles
                    self.on = True
                    self.log.info("Valid generator exhausted, not inserting "
                                  "non-valid cycles anymore")
                    return

            self.log.debug("Will be on for %d cycles, off for %s" %
                           (self.on, self.off))
        else:
            # Valid every clock cycle
            self.on, self.off = True, False
            self.log.debug("Not using valid generator")

    def set_valid_generator(self, valid_generator=None):
        """
        Set a new valid generator for this bus
        """

        self.valid_generator = valid_generator
        self._next_valids()


@cocotb.coroutine
def polled_socket_attachment(driver, sock):
    """
    Non-blocking socket attachment that queues any payload received from the
    socket to be queued for sending into the driver
    """
    import socket, errno
    sock.setblocking(False)
    driver.log.info("Listening for data from %s" % repr(sock))
    while True:
        yield RisingEdge(driver.clock)
        try:
            data = sock.recv(4096)
        except socket.error as e:
            if e.args[0] in [errno.EAGAIN, errno.EWOULDBLOCK]:
                continue
            else:
                driver.log.error(repr(e))
                raise
        if not len(data):
            driver.log.info("Remote end closed the connection")
            break
        driver.append(data)
