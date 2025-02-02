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
from typing import TYPE_CHECKING, Type, Union

import cocotb
from cocotb._py_compat import cached_property
from cocotb._utils import cached_method
from cocotb._write_scheduler import trust_inertial
from cocotb.handle import LogicObject
from cocotb.simulator import clock_create
from cocotb.task import Task
from cocotb.triggers import (
    ClockCycles,
    Event,
    FallingEdge,
    RisingEdge,
    Timer,
    ValueChange,
)
from cocotb.utils import get_sim_steps, get_time_from_sim_steps

if TYPE_CHECKING:  # pragma: no cover
    from typing import Literal, TypeAlias

    Impl: TypeAlias = Literal["gpi"] | Literal["py"]


_valid_impls = ("gpi", "py")


class Clock:
    r"""Simple 50:50 duty cycle clock driver.

    .. code-block:: python

        c = Clock(dut.clk, 10, "ns")
        c.start()

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
    See the environment variable's documentation for more information on the consequences
    of using the simulator's inertial write mechanism.

    If you need more features like a phase shift and an asymmetric duty cycle,
    it is simple to create your own clock generator (that you then :func:`cocotb.start_soon`):

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
        cocotb.start_soon(custom_clock())
        await Timer(1000, units="ns")
        high_delay = low_delay = 10  # change the clock speed
        await Timer(1000, units="ns")

    .. versionchanged:: 1.5
        Support ``'step'`` as the *units* argument to mean "simulator time step".

    .. versionchanged:: 2.0
        Passing ``None`` as the *units* argument was removed, use ``'step'`` instead.

    .. versionchanged:: 2.0
        :meth:`start` now automatically calls :func:`cocotb.start_soon` and stores the Task
        on the Clock object, so that it may later be :meth:`stop`\ ped.
    """

    def __init__(
        self,
        signal: LogicObject,
        period: Union[float, Fraction, Decimal],
        units: str = "step",
        impl: "Impl | None" = None,
    ) -> None:
        self._signal = signal
        self._period = period
        self._units = units
        self._impl: "Impl"  # noqa: UP037  # ruff assumes we are at least using Python 3.7 and gives false positive.

        if impl is None:
            self._impl = "gpi" if trust_inertial else "py"
        elif impl in _valid_impls:
            self._impl = impl
        else:
            valid_impls_str = ", ".join([repr(i) for i in _valid_impls])
            raise ValueError(
                f"Invalid clock impl {impl!r}, must be one of: {valid_impls_str}"
            )

        self._task: Union[Task[None], None] = None

    @property
    def signal(self) -> LogicObject:
        """The clock signal being driven."""
        return self._signal

    @property
    def period(self) -> Union[float, Fraction, Decimal]:
        """The clock period (unitless)."""
        return self._period

    @property
    def units(self) -> str:
        """The unit of the clock period."""
        return self._units

    @property
    def impl(self) -> "Impl":
        """The concrete implementation of the clock used.

        ``"gpi"`` if the clock is implemented in C in the GPI layer,
        or ``"py"`` if the clock is implemented in Python using cocotb Tasks.
        """
        return self._impl

    def start(self, start_high: bool = True) -> Task[None]:
        r"""Start driving the clock signal.

        You can later stop the clock by calling :meth:`stop`.

        Args:
            start_high: Whether to start the clock with a ``1``
                for the first half of the period.
                Default is ``True``.

                .. versionadded:: 1.3

        Raises:
            RuntimeError: If attempting to start a clock that has already been started.

        Returns:
            Object which can be passed to :func:`cocotb.start_soon` or ignored.

        .. versionchanged:: 2.0
            Removed ``cycles`` arguments for toggling for a finite amount of cyles.
            Use :meth:`stop` to stop a clock from running.

        .. versionchanged:: 2.0
            Previously, this method returned a :term:`coroutine` which needed to be passed to :func:`cocotb.start_soon`.
            Now the Clock object keeps track of its own driver Task, so this is no longer necessary.
            Simply call ``clock.start()`` to start running the clock.
        """
        if self._task is not None:
            raise RuntimeError("Starting clock that has already been started.")

        period = get_sim_steps(self._period, self._units)
        t_high = period // 2

        if self._impl == "gpi":
            self._clkobj = clock_create(self._signal._handle)
            self._clkobj.start(period, t_high, start_high)

            async def drive() -> None:
                # The clock is meant to toggle forever, so awaiting this should
                # never return by awaiting on Event that's never set.
                e = Event()
                await e.wait()

        else:

            async def drive() -> None:
                timer_high = Timer(t_high)
                timer_low = Timer(period - t_high)
                if start_high:
                    self._signal.set(1)
                    await timer_high
                while True:
                    self._signal.set(0)
                    await timer_low
                    self._signal.set(1)
                    await timer_high

        self._task = cocotb.start_soon(drive())

        # So if a user calls `task.kill()` on the returned task the Clock object is stopped.
        self._task._add_done_callback(lambda _: self._cleanup())

        return self._task

    def stop(self) -> None:
        """Stop driving the clock signal.

        You can later start the clock again by calling :meth:`start`.

        Raises:
            RuntimeError: If attempting to stop a clock that has never been started.

        .. versionadded:: 2.0
        """
        if self._task is None:
            raise RuntimeError("Stopping a clock that was never started.")
        self._task.kill()
        self._cleanup()

    def _cleanup(self) -> None:
        if self._impl == "gpi":
            self._clkobj.stop()
        self._task = None

    async def cycles(
        self,
        num_cycles: int,
        edge_type: Union[
            Type[RisingEdge], Type[FallingEdge], Type[ValueChange]
        ] = RisingEdge,
    ) -> None:
        """Wait for a number of clock cycles."""
        # TODO Improve implementation to use a Timer to skip most of the cycles
        await ClockCycles(self._signal, num_cycles, edge_type)

    @cached_method
    def __repr__(self) -> str:
        freq_mhz = 1 / get_time_from_sim_steps(
            get_sim_steps(self._period, self._units), "us"
        )
        return f"<{type(self).__qualname__}, {self._signal._path} @ {freq_mhz} MHz>"

    @cached_property
    def log(self) -> Logger:
        return logging.getLogger(
            f"cocotb.{type(self).__qualname__}.{self._signal._name}"
        )
