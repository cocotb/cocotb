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
import warnings
from decimal import Decimal
from numbers import Real
from typing import Union

from cocotb.log import SimLog
from cocotb.triggers import Timer
from cocotb.utils import get_sim_steps, get_time_from_sim_steps, lazy_property


class BaseClock:
    """Base class to derive from."""

    def __init__(self, signal):
        self.signal = signal

    @lazy_property
    def log(self):
        return SimLog("cocotb.{}.{}".format(type(self).__qualname__, self.signal._name))


class Clock(BaseClock):
    r"""Simple 50:50 duty cycle clock driver.

    Instances of this class should call its :meth:`start` method
    and pass the coroutine object to one of the functions in :ref:`task-management`.

    This will create a clocking task that drives the signal at the
    desired period/frequency.

    Example:

    .. code-block:: python

        c = Clock(dut.clk, 10, 'ns')
        await cocotb.start(c.start())

    Args:
        signal: The clock pin/signal to be driven.
        period (int): The clock period. Must convert to an even number of
            timesteps.
        units (str, optional): One of
            ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When *units* is ``'step'``,
            the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).

    If you need more features like a phase shift and an asymmetric duty cycle,
    it is simple to create your own clock generator (that you then :func:`~cocotb.start`):

    .. code-block:: python

        async def custom_clock():
            # pre-construct triggers for performance
            high_time = Timer(high_delay, units="ns")
            low_time = Timer(low_delay, units="ns")
            await Timer(initial_delay, units="ns")
            while True:
                dut.clk.value = 1
                await high_time
                dut.clk.value = 0
                await low_time

    If you also want to change the timing during simulation,
    use this slightly more inefficient example instead where
    the :class:`Timer`\ s inside the while loop are created with
    current delay values:

    .. code-block:: python

        async def custom_clock():
            while True:
                dut.clk.value = 1
                await Timer(high_delay, units="ns")
                dut.clk.value = 0
                await Timer(low_delay, units="ns")

        high_delay = low_delay = 100
        await cocotb.start(custom_clock())
        await Timer(1000, units="ns")
        high_delay = low_delay = 10  # change the clock speed
        await Timer(1000, units="ns")

    .. versionchanged:: 1.5
        Support ``'step'`` as the *units* argument to mean "simulator time step".

    .. deprecated:: 1.5
        Using ``None`` as the *units* argument is deprecated, use ``'step'`` instead.
    """

    def __init__(
        self, signal, period: Union[float, Real, Decimal], units: str = "step"
    ):
        BaseClock.__init__(self, signal)
        if units is None:
            warnings.warn(
                'Using units=None is deprecated, use units="step" instead.',
                DeprecationWarning,
                stacklevel=2,
            )
            units = "step"  # don't propagate deprecated value
        self.period = get_sim_steps(period, units)
        self.half_period = get_sim_steps(period / 2, units)
        self.frequency = 1 / get_time_from_sim_steps(self.period, units="us")
        self.hdl = None
        self.signal = signal
        self.coro = None
        self.mcoro = None

    async def start(self, cycles=None, start_high=True):
        r"""Clocking coroutine.  Start driving your clock by :func:`cocotb.start`\ ing a
        call to this.

        Args:
            cycles (int, optional): Cycle the clock *cycles* number of times,
                or if ``None`` then cycle the clock forever.
                Note: ``0`` is not the same as ``None``, as ``0`` will cycle no times.
            start_high (bool, optional): Whether to start the clock with a ``1``
                for the first half of the period.
                Default is ``True``.

                .. versionadded:: 1.3
        """
        t = Timer(self.half_period)
        if cycles is None:
            it = itertools.count()
        else:
            it = range(cycles)

        # branch outside for loop for performance (decision has to be taken only once)
        if start_high:
            for _ in it:
                self.signal.value = 1
                await t
                self.signal.value = 0
                await t
        else:
            for _ in it:
                self.signal.value = 0
                await t
                self.signal.value = 1
                await t

    def __str__(self):
        return type(self).__qualname__ + "(%3.1f MHz)" % self.frequency
