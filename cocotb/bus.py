#!/usr/bin/env python

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
    Common bus related functionality

    A bus is simply defined as a collection of signals
"""

class Bus(object):
    """
        Wraps up a collection of signals
    """
    def __init__(self, entity, name, signals):
        """
        entity:         SimHandle instance to the entity containing the bus
        name:           name of the bus
        signals:        array of signal names
        """
        for signal in signals:
            signame = name + "_" + signal
            setattr(self, signal, getattr(entity, signame))

        self._signals = {}
        self._signals[signal] = getattr(self, signal)
        self._entity = entity
        self._name = name

    def drive(self, obj):
        """
        Drives values onto the bus.

        obj is an object with attribute names that match the bus signals
        """
        for name, hdl in self._signals.items():
            if not hasattr(obj, name):
                raise AttributeError("Unable to drive onto %s.%s because %s is missing attribute %s" %
                        (self._entity.name, self._name, obj.__class__.__name__, name))
            hdl <= getattr(obj, name)
