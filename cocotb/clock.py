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
    A clock class
"""
import simulator

from cocotb.log import SimLog

class BaseClock(object):
    """Base class to derive from"""
    def __init__(self, signal):
        self.signal = signal
        self.log = SimLog("cocotb.%s.%s" % (self.__class__.__name__, self.signal.name))

class Clock(BaseClock):
    """
    simple 50:50 duty cycle clock
    """
    def __init__(self, signal, period):
        BaseClock.__init__(self, signal)
        self.period = period
        self.frequency = 1.0 / period * 1000000
        self.hdl = None


    def start(self, cycles=0):
        """
        cycles = 0 will not auto stop the clock
        """
        if self.hdl is None:
            self.hdl = simulator.create_clock(self.signal._handle, self.period, cycles)
            self.log.info("Clock %s Started with period %d" % (str(self.signal), self.period))
        else:
            self.log.debug("Clock %s already started" % (str(self.signal)))

    def stop(self):
        if self.hdl is not None:
            simulator.stop_clock(self.hdl)
            self.log.info("Clock %s Stopped" % (str(self.signal)))
            self.hdl = None
        else:
            self.log.debug("Clock %s already stopped" % (str(self.signal)))

    def __str__(self):
        return self.__class__.__name__ + "(%3.1fMHz)" % self.frequency
