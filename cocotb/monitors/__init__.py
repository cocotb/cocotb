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

    Class defining the standard interface for a monitor within a testbench

    The monitor is responsible for watching the pins of the DUT and recreating
    the transactions
"""

import math
from collections import deque

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Edge, Event, RisingEdge, ReadOnly, Timer
from cocotb.binary import BinaryValue
from cocotb.bus import Bus
from cocotb.log import SimLog
from cocotb.result import ReturnValue


class MonitorStatistics(object):
    """Wrapper class for storing Monitor statistics"""
    def __init__(self):
        self.received_transactions = 0


class Monitor(object):

    def __init__(self, callback=None, event=None):
        """
        Constructor for a monitor instance

        callback will be called with each recovered transaction as the argument

        If the callback isn't used, received transactions will be placed on a
        queue and the event used to notify any consumers.
        """
        self._event = event
        self._wait_event = None
        self._recvQ = deque()
        self._callbacks = []
        self.stats = MonitorStatistics()
        self._wait_event = Event()

        # Subclasses may already set up logging
        if not hasattr(self, "log"):
            self.log = SimLog("cocotb.monitor.%s" % (self.__class__.__name__))

        if callback is not None:
            self.add_callback(callback)

        # Create an independent coroutine which can receive stuff
        self._thread = cocotb.scheduler.add(self._monitor_recv())

    def kill(self):
        if self._thread:
            self._thread.kill()
            self._thread = None

    def __len__(self):
        return len(self._recvQ)

    def __getitem__(self, idx):
        return self._recvQ[idx]

    def add_callback(self, callback):
        self.log.debug("Adding callback of function %s to monitor" %
                       (callback.__name__))
        self._callbacks.append(callback)

    @coroutine
    def wait_for_recv(self, timeout=None):
        if timeout:
            t = Timer(timeout)
            fired = yield [self._wait_event.wait(), t]
            if fired is t:
                raise ReturnValue(None)
        else:
            yield self._wait_event.wait()

        pkt = self._wait_event.data
        raise ReturnValue(pkt)

    @coroutine
    def _monitor_recv(self):
        """
        actual impementation of the receiver

        subclasses should override this method to implement the actual receive
        routine and call self._recv() with the recovered transaction
        """
        raise NotImplementedError("Attempt to use base monitor class without "
                                  "providing a _monitor_recv method")

    def _recv(self, transaction):
        """Common handling of a received transaction."""

        self.stats.received_transactions += 1

        # either callback based consumer
        for callback in self._callbacks:
            callback(transaction)

        # Or queued with a notification
        if not self._callbacks:
            self._recvQ.append(transaction)

        if self._event is not None:
            self._event.set()

        # If anyone was waiting then let them know
        if self._wait_event is not None:
            self._wait_event.set(data=transaction)
            self._wait_event.clear()


class BusMonitor(Monitor):
    """
    Wrapper providing common functionality for monitoring busses
    """
    _signals = []
    _optional_signals = []

    def __init__(self, entity, name, clock, reset=None, reset_n=None,
                 callback=None, event=None):
        self.log = SimLog("cocotb.%s.%s" % (entity._name, name))
        self.entity = entity
        self.name = name
        self.clock = clock
        self.bus = Bus(self.entity, self.name, self._signals,
                       optional_signals=self._optional_signals)
        self._reset = reset
        self._reset_n = reset_n
        Monitor.__init__(self, callback=callback, event=event)

    @property
    def in_reset(self):
        if self._reset_n is not None:
            return not bool(self._reset_n.value.integer)
        if self._reset is not None:
            return bool(self._reset.value.integer)
        return False

    def __str__(self):
        return "%s(%s)" % (self.__class__.__name__, self.name)
