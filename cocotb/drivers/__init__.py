#!/bin/env python

# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
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

"""Set of common driver base classes."""

from collections import deque

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import (Event, RisingEdge, ReadOnly, NextTimeStep,
                             Edge)
from cocotb.bus import Bus
from cocotb.log import SimLog
from cocotb.utils import reject_remaining_kwargs


class BitDriver(object):
    """Drives a signal onto a single bit.

    Useful for exercising ready / valid.
    """
    def __init__(self, signal, clk, generator=None):
        self._signal = signal
        self._clk = clk
        self._generator = generator

    def start(self, generator=None):
        """Start generating data.

        Args:
            generator (optional): Generator yielding data.
        """
        self._cr = cocotb.fork(self._cr_twiddler(generator=generator))

    def stop(self):
        """Stop generating data."""
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
    """Class defining the standard interface for a driver within a testbench.

    The driver is responsible for serialising transactions onto the physical
    pins of the interface.  This may consume simulation time.
    """
    def __init__(self):
        """Constructor for a driver instance."""
        self._pending = Event(name="Driver._pending")
        self._sendQ = deque()

        # Subclasses may already set up logging
        if not hasattr(self, "log"):
            self.log = SimLog("cocotb.driver.%s" % (self.__class__.__name__))

        # Create an independent coroutine which can send stuff
        self._thread = cocotb.scheduler.add(self._send_thread())

    def kill(self):
        """Kill the coroutine sending stuff."""
        if self._thread:
            self._thread.kill()
            self._thread = None

    def append(self, transaction, callback=None, event=None, **kwargs):
        """Queue up a transaction to be sent over the bus.

        Mechanisms are provided to permit the caller to know when the
        transaction is processed.

        Args:
            transaction (any): The transaction to be sent.
            callback (callable, optional): Optional function to be called 
                when the transaction has been sent.
            event (optional): :class:`~cocotb.triggers.Event` to be set
                when the transaction has been sent.
            **kwargs: Any additional arguments used in child class' 
                :any:`_driver_send` method.
        """
        self._sendQ.append((transaction, callback, event, kwargs))
        self._pending.set()

    def clear(self):
        """Clear any queued transactions without sending them onto the bus."""
        self._sendQ = deque()

    @coroutine
    def send(self, transaction, sync=True, **kwargs):
        """Blocking send call (hence must be "yielded" rather than called).

        Sends the transaction over the bus.

        Args:
            transaction (any): The transaction to be sent.
            sync (bool, optional): Synchronise the transfer by waiting for a rising edge.
            **kwargs (dict): Additional arguments used in child class'
                :any:`_driver_send` method.
        """
        yield self._send(transaction, None, None, sync=sync, **kwargs)

    def _driver_send(self, transaction, sync=True, **kwargs):
        """Actual implementation of the send.

        Subclasses should override this method to implement the actual 
        :meth:`~cocotb.drivers.Driver.send` routine.

        Args:
            transaction (any): The transaction to be sent.
            sync (boolean, optional): Synchronise the transfer by waiting for a rising edge.
            **kwargs: Additional arguments if required for protocol implemented in subclass.
        """
        raise NotImplementedError("Subclasses of Driver should define a "
                                  "_driver_send coroutine")

    @coroutine
    def _send(self, transaction, callback, event, sync=True, **kwargs):
        """Send coroutine.

        Args:
            transaction (any): The transaction to be sent.
            callback (callable, optional): Optional function to be called 
                when the transaction has been sent.
            event (optional): event to be set when the transaction has been sent.
            sync (boolean, optional): Synchronise the transfer by waiting for a rising edge.
            **kwargs: Any additional arguments used in child class' 
                :any:`_driver_send` method.
        """
        yield self._driver_send(transaction, sync=sync, **kwargs)

        # Notify the world that this transaction is complete
        if event:
            event.set()
        if callback:
            callback(transaction)

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
                transaction, callback, event, kwargs = self._sendQ.popleft()
                self.log.debug("Sending queued packet...")
                yield self._send(transaction, callback, event,
                                 sync=not synchronised, **kwargs)
                synchronised = True


class BusDriver(Driver):
    """Wrapper around common functionality for busses which have:

        * a list of :attr:`_signals` (class attribute)
        * a list of :attr:`_optional_signals` (class attribute)
        * a clock
        * a name
        * an entity

        Args:
            entity (SimHandle): A handle to the simulator entity.
            name (str or None): Name of this bus. ``None`` for nameless bus, e.g.
                bus-signals in an interface or a modport.
                (untested on struct/record, but could work here as well).
            clock (SimHandle): A handle to the clock associated with this bus.
            array_idx (int or None, optional): Optional index when signal is an array.
    """
    
    _optional_signals = []

    def __init__(self, entity, name, clock, **kwargs):
        # emulate keyword-only arguments in python 2
        index = kwargs.pop("array_idx", None)
        reject_remaining_kwargs('__init__', kwargs)

        self.log = SimLog("cocotb.%s.%s" % (entity._name, name))
        Driver.__init__(self)
        self.entity = entity
        self.clock = clock
        self.bus = Bus(self.entity, name, self._signals,
                       self._optional_signals, array_idx=index)

        # Give this instance a unique name
        self.name = name if index is None else "%s_%d" % (name, index)

    @coroutine
    def _driver_send(self, transaction, sync=True):
        """Implementation for BusDriver.

        Args:
            transaction: The transaction to send.
            sync (bool, optional): Synchronise the transfer by waiting for a rising edge.
        """
        if sync:
            yield RisingEdge(self.clock)
        self.bus <= transaction

    @coroutine
    def _wait_for_signal(self, signal):
        """This method will return when the specified signal
        has hit logic ``1``. The state will be in the 
        :class:`~cocotb.triggers.ReadOnly` phase so sim will need
        to move to :class:`~cocotb.triggers.NextTimeStep` before
        registering more callbacks can occur.
        """
        yield ReadOnly()
        while signal.value.integer != 1:
            yield RisingEdge(signal)
            yield ReadOnly()
        yield NextTimeStep()

    @coroutine
    def _wait_for_nsignal(self, signal):
        """This method will return when the specified signal
        has hit logic ``0``. The state will be in the 
        :class:`~cocotb.triggers.ReadOnly` phase so sim will need
        to move to :class:`~cocotb.triggers.NextTimeStep` before
        registering more callbacks can occur.
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
    """Same as a BusDriver except we support an optional generator to control
    which cycles are valid.

    Args:
        entity (SimHandle): A handle to the simulator entity.
        name (str): Name of this bus.
        clock (SimHandle): A handle to the clock associated with this bus.
        valid_generator (generator, optional): a generator that yields tuples  of
            (valid, invalid) cycles to insert.
    """

    def __init__(self, entity, name, clock, **kwargs):
        valid_generator = kwargs.pop("valid_generator", None)
        BusDriver.__init__(self, entity, name, clock, **kwargs)
        self.set_valid_generator(valid_generator=valid_generator)

    def _next_valids(self):
        """Optionally insert invalid cycles every N cycles
        Generator should return a tuple with the number of cycles to be
        on followed by the number of cycles to be off.
        The 'on' cycles should be non-zero, we skip invalid generator entries.
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
        """Set a new valid generator for this bus."""
        self.valid_generator = valid_generator
        self._next_valids()


@cocotb.coroutine
def polled_socket_attachment(driver, sock):
    """Non-blocking socket attachment that queues any payload received from the
    socket to be queued for sending into the driver.
    """
    import socket
    import errno
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
