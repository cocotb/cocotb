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
from cocotb.drivers import Driver

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
