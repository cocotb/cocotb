#!/usr/bin/env python

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
    Common bus related functionality

    A bus is simply defined as a collection of signals
"""
from cocotb.result import TestError


class Bus(object):
    """
        Wraps up a collection of signals

        Assumes we have a set of signals/nets named:

            entity.bus_name_signal

        for example a bus named "stream_in" with signals ["valid", "data"]
            dut.stream_in_valid
            dut.stream_in_data

        TODO:
            Support for struct/record ports where signals are member names
    """
    def __init__(self, entity, name, signals, optional_signals=[]):
        """
        Args:
            entity (SimHandle): SimHandle instance to the entity containing the
                                bus
            name (str):         name of the bus. None for nameless bus, e.g.
                                bus-signals in an interface or a modport
                                (untested on struct/record, but could work here
                                as well)
            signals (list):     array of signal names

        Kwargs:
            optiona_signals (list): array of optional signal names
        """
        self._entity = entity
        self._name = name
        self._signals = {}

        for signal in signals:
            if name:
                signame = name + "_" + signal
            else:
                signame = signal
            setattr(self, signal, getattr(entity, signame))
            self._signals[signal] = getattr(self, signal)

        # Also support a set of optional signals that don't have to be present
        for signal in optional_signals:
            if name:
                signame = name + "_" + signal
            else:
                signame = signal
            # Attempts to access a signal that doesn't exist will print a
            # backtrace so we 'peek' first, slightly un-pythonic
            if entity.__hasattr__(signame):
                hdl = getattr(entity, signame)
                setattr(self, signal, hdl)
                self._signals[signal] = getattr(self, signal)
            else:
                self._entity._log.debug("Ignoring optional missing signal "
                                        "%s on bus %s" % (signal, name))

    def drive(self, obj, strict=False):
        """
        Drives values onto the bus.

        Args:
            obj (any type) : object with attribute names that match the bus
                             signals

        Kwargs:
            strict (bool)  : Check that all signals are being assigned

        Raises:
            AttributeError
        """
        for name, hdl in self._signals.items():
            if not hasattr(obj, name):
                if strict:
                    msg = ("Unable to drive onto %s.%s because %s is missing "
                           "attribute %s" % self._entity._name, self._name,
                           obj.__class__.__name__, name)
                    raise AttributeError(msg)
                else:
                    continue
            val = getattr(obj, name)
            hdl <= val

    def __le__(self, value):
        """Overload the less than or equal to operator for value assignment"""
        self.drive(value)
