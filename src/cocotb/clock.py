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

import logging
from decimal import Decimal
from fractions import Fraction
from logging import Logger
from typing import Union

import cocotb._conf
from cocotb._py_compat import cached_property
from cocotb.sim_time_utils import get_sim_steps, get_time_from_sim_steps
from cocotb.simulator import clock_create
from cocotb.triggers import Event, Timer


class Clock:
    r"""Simple 50:50 duty cycle clock driver.

    Instances of this class should call its :meth:`start` method
    and pass the coroutine object to one of the functions in :ref:`task-management`.

    This will create a clocking task that drives the signal at the
    desired period/frequency.

    Example:

    .. code-block:: python

        c = Clock(dut.clk, 10, "ns")
        await cocotb.start(c.start())

    Args:
        signal: The clock pin/signal to be driven.
        period: The clock period. Must convert to an even number of
            timesteps.
        units: One of
            ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When *units* is ``'step'``,
            the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).
        impl: One of
            ``'auto'``, ``'gpi'``, ``'py'``.
            Specify whether the clock is implemented with a :class:`~cocotb.simulator.GpiClock` (faster), or with a Python coroutine.
            When ``'auto'`` is used (default), the fastest implementation that supports your environment and use case is picked.

            .. versionadded:: 2.0

    When *impl* is ``'auto'``, if :envvar:`COCOTB_TRUST_INERTIAL_WRITES` is defined,
    the :class:`~cocotb.simulator.GpiClock` implementation will be used.
    Otherwise, the Python coroutine implementation will be used.
    See the environment variable documentation for more information on the consequences
    of using the simulator's inertial write mechanism.

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

    .. versionchanged:: 2.0
        Passing ``None`` as the *units* argument was removed, use ``'step'`` instead.
    """

    def __init__(
        self,
        signal,
        period: Union[float, Fraction, Decimal],
        units: str = "step",
        impl: str = "auto",
    ):
        self.signal = signal
        self.period = get_sim_steps(period, units)
        self.frequency = 1 / get_time_from_sim_steps(self.period, units="us")
        valid_impls = ["auto", "gpi", "py"]
        if impl not in valid_impls:
            valid_impls_str = ", ".join([repr(i) for i in valid_impls])
            raise ValueError(
                f"Invalid clock impl {impl!r}, must be one of: {valid_impls_str}"
            )
        if impl == "auto":
            impl = "gpi" if cocotb._conf.trust_inertial else "py"
        self.impl = impl

    async def start(self, start_high: bool = True) -> None:
        r"""Clocking coroutine.  Start driving your clock by :func:`cocotb.start`\ ing a
        call to this.

        Args:
            start_high: Whether to start the clock with a ``1``
                for the first half of the period.
                Default is ``True``.

                .. versionadded:: 1.3

        .. versionchanged:: 2.0
            Removed ``cycles`` arguments for toggling for a finite amount of cyles.
            Use ``kill()`` on the clock task instead, or implement manually.
        """

        t_high = self.period // 2

        if self.impl == "gpi":
            clkobj = clock_create(self.signal._handle)
            clkobj.start(self.period, t_high, start_high)

            try:
                # The clock is meant to toggle forever, so awaiting this should
                # never return (except in case of CancelledError).
                # Await on an event that's never set.
                e = Event()
                await e.wait()
            finally:
                clkobj.stop()
        else:
            timer_high = Timer(t_high)
            timer_low = Timer(self.period - t_high)
            if start_high:
                self.signal.value = 1
                await timer_high
            while True:
                self.signal.value = 0
                await timer_low
                self.signal.value = 1
                await timer_high

    def __str__(self) -> str:
        return type(self).__qualname__ + f"({self.frequency:3.1f} MHz)"

    @cached_property
    def log(self) -> Logger:
        return logging.getLogger(
            f"cocotb.{type(self).__qualname__}.{self.signal._name}"
        )
