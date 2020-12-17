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
from typing import Union, Tuple, Optional
import warnings

import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Timer
from cocotb.utils import get_sim_steps, get_time_from_sim_steps, lazy_property
from cocotb.handle import SimHandleBase

_logger = SimLog(__name__)


class BaseClock:
    """Base class to derive from."""

    def __init__(self, signal):
        self.signal = signal

    @lazy_property
    def log(self):
        return SimLog("cocotb.%s.%s" % (
            type(self).__qualname__, self.signal._name
        ))


class Clock(BaseClock):
    r"""Simple 50:50 duty cycle clock driver.

    Instances of this class should call its :meth:`start` method and :func:`fork` the
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
            ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When *units* is ``'step'``,
            the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).

    If you need more features like a phase shift and an asymmetric duty cycle,
    it is simple to create your own clock generator (that you then :func:`fork`):

    .. code-block:: python

        async def custom_clock():
            # pre-construct triggers for performance
            high_time = Timer(high_delay, units="ns")
            low_time = Timer(low_delay, units="ns")
            await Timer(initial_delay, units="ns")
            while True:
                dut.clk <= 1
                await high_time
                dut.clk <= 0
                await low_time

    If you also want to change the timing during simulation,
    use this slightly more inefficient example instead where
    the :class:`Timer`\ s inside the while loop are created with
    current delay values:

    .. code-block:: python

        async def custom_clock():
            while True:
                dut.clk <= 1
                await Timer(high_delay, units="ns")
                dut.clk <= 0
                await Timer(low_delay, units="ns")

        high_delay = low_delay = 100
        cocotb.fork(custom_clock())
        await Timer(1000, units="ns")
        high_delay = low_delay = 10  # change the clock speed
        await Timer(1000, units="ns")

    .. versionchanged:: 1.5
        Support ``'step'`` as the the *units* argument to mean "simulator time step".

    .. deprecated:: 1.5
        Using None as the the *units* argument is deprecated, use ``'step'`` instead.
    """

    def __init__(self, signal, period, units="step"):
        BaseClock.__init__(self, signal)
        if units is None:
            warnings.warn(
                'Using units=None is deprecated, use units="step" instead.',
                DeprecationWarning, stacklevel=2)
            units="step"  # don't propagate deprecated value
        self.period = get_sim_steps(period, units)
        self.half_period = get_sim_steps(period / 2.0, units)
        self.frequency = 1.0 / get_time_from_sim_steps(self.period, units='us')
        self.hdl = None
        self.signal = signal
        self.coro = None
        self.mcoro = None

    async def start(self, cycles=None, start_high=True):
        r"""Clocking coroutine.  Start driving your clock by :func:`fork`\ ing a
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
                self.signal <= 1
                await t
                self.signal <= 0
                await t
        else:
            for _ in it:
                self.signal <= 0
                await t
                self.signal <= 1
                await t

    def __str__(self):
        return type(self).__qualname__ + "(%3.1f MHz)" % self.frequency


class CClock:
    r"""High performance, configurable simulator clock driver.

    This class is a wrapper for a C++ layer clock driver with methods for control.
    Use :meth:`start` to start the clock driver and :meth:`stop` to stop it.
    The :attr:`is_running` property returns whether the driver is active.

    Example:

    .. code-block:: python

        # 0.5 duty cycle by default
        c = CClock(dut.clk, 100, units='ns')
        c.start()

    Args:
        signal: The clock signal to be driven.
        period: The clock period in *units*.
        units: One of
            ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When *units* is ``'step'``,
            the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).
        duty_cycle: The clock duty cycle as a float in [0, 1].
            Duty cycle is defined as the fraction of the period where the clock is high.
            Default is 0.5.

            .. note::
                Duty cycles of 0 or 1 may cause glitches or unexpected simulator behavior.

        jitter: Maximum jitter for one clock period in *units*.
            Default is 0.

    Raises:
        ValueError: If duty cycle value is not in [0, 1].

    If clock jitter is non-zero, random edge-to-edge clock jitter will be generated
    using a normal (gaussian) distribution for the jitter values.
    With a clock period defined as one rising edge to the next rising edge, the jitter
    will be bounded each clock period by ``[-jitter, +jitter]``.

    Jitter example:

    .. code-block:: python

        # 1MHz clock with 10ns of jitter
        c = CClock(dut.clk, 1000, units='ns', jitter=10)
        c.start()

    .. versionadded:: 1.5
    """
    def __init__(
        self, signal: SimHandleBase,
        period: Union[int, float],
        units: str = 'step',
        duty_cycle: Optional[float] = 0.5,
        jitter: Union[int, float] = 0
    ):
        self.signal = signal

        if not 0.0 <= duty_cycle <= 1.0:
            raise ValueError("Duty cycle must be in range [0, 1]")

        if duty_cycle == 0.0 or duty_cycle == 1.0:
            warnings.warn("Duty cycles of 0 or 1 may cause glitches or unexpected simulator behavior",
                          category=RuntimeWarning)

        period_steps = get_sim_steps(period, units)

        high_steps = round(period_steps * duty_cycle)
        low_steps = period_steps - high_steps

        # Divide jitter budget between high and low, scaled to duty cycle
        jitter_steps = get_sim_steps(jitter, units)
        high_jitter = round(jitter_steps * duty_cycle)
        low_jitter = jitter_steps - high_jitter

        _logger.debug("Creating simulator.sim_clock with ({}, {}, {}, {}, {})".format(
            self.signal._name, high_steps, low_steps, high_jitter, low_jitter))

        self._sim_clk = cocotb.simulator.create_clock(
            self.signal._handle, high_steps, low_steps,
            high_jitter, low_jitter)

        # All simulator clocks must be tracked by the scheduler for cleanup between tests
        cocotb.scheduler._add_sim_clock(self._sim_clk)

    @classmethod
    def from_period_tuple(
        cls, signal: SimHandleBase,
        period: Tuple[Union[int, float], Union[int, float]],
        units: str = 'step',
        jitter: Union[int, float] = 0
    ):
        """Create CClock by using separate high and low clock times.

        Example:

        .. code-block:: python

            c = CClock.from_period_tuple(dut.clk, (60, 40), units='ns')
            c.start()

        Args:
            signal: The clock signal to be driven.
            period: The clock period as a 2-tuple of (high_time, low_time) in *units*.
            units: One of
                ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
                When *units* is ``'step'``,
                the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).
            jitter: Maximum jitter for one clock period in *units*.
                Default is 0.
        """
        if not isinstance(period, tuple):
            raise TypeError("Clock period must be a 2-tuple")

        if len(period) != 2:
            raise ValueError("Clock period tuple must have 2 members")

        high_steps = get_sim_steps(period[0], units)
        low_steps = get_sim_steps(period[1], units)
        period = high_steps + low_steps

        duty_cycle = high_steps / period

        return cls(signal, period, 'step', duty_cycle, jitter)

    def start(self, *, periods: Optional[int] = None, posedge_first: bool = True):
        """Start driving the clock.

        Args:
            periods: Drive the clock for this many periods,
                or if ``None`` then drive the clock forever.

                .. note::
                    ``0`` is not the same as ``None``, as ``0`` will not start the clock.

            posedge_first: If ``True``, start driving the clock with the
                positive-going edge at the start of the high part of the period.
                If ``False``, start driving with the negative-going edge.
                This is not the same as inverting the clock.
                Default is ``True``.

        Raises:
            ValueError: If *periods* is negative.
        """
        if periods == 0:
            return

        if periods is None:
            toggles = 0
        else:
            if periods < 0:
                raise ValueError("Periods value must be a non-negative integer")
            toggles = periods * 2

        self._sim_clk.start(toggles, posedge_first)

    def stop(self):
        """Stop driving the clock."""
        self._sim_clk.stop()

    @property
    def is_running(self) -> bool:
        """Active status of the clock driver."""
        return self._sim_clk.is_running()
