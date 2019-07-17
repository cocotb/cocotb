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

"""A clock class."""

import itertools

import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Timer
from cocotb.utils import get_sim_steps, get_time_from_sim_steps, lazy_property


class BaseClock(object):
    """Base class to derive from."""
    def __init__(self, signal):
        self.signal = signal

    @lazy_property
    def log(self):
        return SimLog("cocotb.%s.%s" % (
            self.__class__.__name__, self.signal._name
        ))


class Clock(BaseClock):
    """Simple 50:50 duty cycle clock driver.

    Instances of this class should call its :meth:`start` method and fork the
    result.  This will create a clocking thread that drives the signal at the
    desired period/frequency.

    Example:

    .. code-block:: python

        c = Clock(dut.clk, 10, 'ns')
        cocotb.fork(c.start())

    Args:
        signal: The clock pin/signal to be driven.
        period (int): The clock period. Must convert to an even number of
            timesteps.
        units (str, optional): One of 
            ``None``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When no *units* is given (``None``) the timestep is determined by
            the simulator.
    """
    
    def __init__(self, signal, period, units=None):
        BaseClock.__init__(self, signal)
        self.period = get_sim_steps(period, units)
        self.half_period = get_sim_steps(period / 2.0, units)
        self.frequency = 1.0 / get_time_from_sim_steps(self.period,units='us')
        self.hdl = None
        self.signal = signal
        self.coro = None
        self.mcoro = None

    @cocotb.coroutine
    def start(self, cycles=None):
        """Clocking coroutine.  Start driving your clock by forking a 
        call to this.

        Args:
            cycles (int, optional): Cycle the clock *cycles* number of times,
                or if ``None`` then cycle the clock forever. 
                Note: ``0`` is not the same as ``None``, as ``0`` will cycle no times.
        """
        t = Timer(self.half_period)
        if cycles is None:
            it = itertools.count()
        else:
            it = range(cycles)

        for _ in it:
            self.signal <= 1
            yield t
            self.signal <= 0
            yield t

    def __str__(self):
        return self.__class__.__name__ + "(%3.1f MHz)" % self.frequency
