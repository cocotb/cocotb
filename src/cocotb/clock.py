# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""A clock class."""

import logging
import warnings
from decimal import Decimal
from fractions import Fraction
from logging import Logger
from typing import ClassVar, Type, Union

import cocotb
from cocotb._py_compat import (
    Literal,
    TypeAlias,
    cached_property,
)
from cocotb._typing import TimeUnit
from cocotb.handle import (
    Deposit,
    Force,
    Immediate,
    LogicObject,
    _GPISetAction,
    _trust_inertial,
)
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

__all__ = ("Clock",)

Impl: TypeAlias = Literal["gpi", "py"]


_valid_impls = ("gpi", "py")


class Clock:
    r"""Simple 50:50 duty cycle clock driver.

    .. code-block:: python

        c = Clock(dut.clk, 10, "ns")
        c.start()

    Args:
        signal: The clock pin/signal to be driven.
        period: The clock period.

            .. note::
                Must convert to an even number of timesteps.
        unit:
            One of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When *unit* is ``'step'``,
            the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).

            .. versionchanged:: 2.0
                Renamed from ``units``.

        impl:
            One of ``'auto'``, ``'gpi'``, ``'py'``.
            Specify whether the clock is implemented with a :class:`~cocotb.simulator.GpiClock` (faster), or with a Python coroutine.
            When ``'auto'`` is used (default), the fastest implementation that supports your environment and use case is picked.

            .. versionadded:: 2.0

        set_action:
            One of :class:`.Immediate`, :class:`.Deposit`, or :class:`.Force`.
            Specify the action to use when setting the clock signal value.
            Defaults to the value of :attr:`default_set_action`.

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
            high_time = Timer(high_delay, unit="ns")
            low_time = Timer(low_delay, unit="ns")
            await Timer(initial_delay, unit="ns")
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
                await Timer(high_delay, unit="ns")
                dut.clk.value = 0
                await Timer(low_delay, unit="ns")


        high_delay = low_delay = 100
        cocotb.start_soon(custom_clock())
        await Timer(1000, unit="ns")
        high_delay = low_delay = 10  # change the clock speed
        await Timer(1000, unit="ns")

    .. versionadded:: 1.5
        Support ``'step'`` as the *unit* argument to mean "simulator time step".

    .. versionremoved:: 2.0
        Passing ``None`` as the *unit* argument was removed, use ``'step'`` instead.

    .. versionchanged:: 2.0
        :meth:`start` now automatically calls :func:`cocotb.start_soon` and stores the Task
        on the Clock object, so that it may later be :meth:`stop`\ ped.
    """

    _impl: Impl

    default_set_action: ClassVar[Union[Type[Immediate], Type[Deposit], Type[Force]]] = (
        Deposit
    )
    """The default action used to set the clock signal value.
    One of :class:`.Immediate`, :class:`.Deposit`, or :class:`.Force`.

    .. versionadded:: 2.0
    """

    def __init__(
        self,
        signal: LogicObject,
        period: Union[float, Fraction, Decimal],
        unit: TimeUnit = "step",
        impl: Union[Impl, None] = None,
        *,
        units: None = None,
        set_action: Union[Type[Immediate], Type[Deposit], Type[Force], None] = None,
    ) -> None:
        self._signal = signal
        self._period = period
        if units is not None:
            warnings.warn(
                "The 'units' argument has been renamed to 'unit'.",
                DeprecationWarning,
                stacklevel=2,
            )
            unit = units
        self._unit: TimeUnit = unit
        if set_action is None:
            set_action = type(self).default_set_action
        if set_action not in (Immediate, Deposit, Force):
            raise TypeError(
                "Invalid value for *set_action*. *set_action* must be one of Immediate, Deposit, or Force"
            )
        self._set_action = set_action

        if impl is None:
            self._impl = "gpi" if _trust_inertial else "py"
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
        """The clock period (unit-less)."""
        return self._period

    @property
    def unit(self) -> TimeUnit:
        """The unit of the clock period.

        .. versionadded:: 2.0
        """
        return self._unit

    @property
    def impl(self) -> Impl:
        """The concrete implementation of the clock used.

        ``"gpi"`` if the clock is implemented in C in the GPI layer,
        or ``"py"`` if the clock is implemented in Python using cocotb Tasks.

        .. versionadded:: 2.0
        """
        return self._impl

    @property
    def set_action(self) -> Union[Type[Immediate], Type[Deposit], Type[Force]]:
        """The value setting action used to set the clock signal value.

        .. versionadded:: 2.0
        """
        return self._set_action

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

        .. versionremoved:: 2.0
            Removed ``cycles`` arguments for toggling for a finite amount of cycles.
            Use :meth:`stop` to stop a clock from running.

        .. versionchanged:: 2.0
            Previously, this method returned a :term:`coroutine` which needed to be passed to :func:`cocotb.start_soon`.
            Now the Clock object keeps track of its own driver Task, so this is no longer necessary.
            Simply call ``clock.start()`` to start running the clock.
        """
        if self._task is not None:
            raise RuntimeError("Starting clock that has already been started.")

        period = get_sim_steps(self._period, self._unit)
        t_high = period // 2

        if self._impl == "gpi":
            clkobj = clock_create(self._signal._handle)
            set_action = {
                Deposit: _GPISetAction.DEPOSIT,
                Immediate: _GPISetAction.NO_DELAY,
                Force: _GPISetAction.FORCE,
            }[self._set_action]
            clkobj.start(period, t_high, start_high, set_action)

            async def drive() -> None:
                # The clock is meant to toggle forever, so awaiting this should
                # never return by awaiting on Event that's never set.
                e = Event()
                try:
                    await e.wait()
                finally:
                    clkobj.stop()

        else:

            async def drive() -> None:
                timer_high = Timer(t_high)
                timer_low = Timer(period - t_high)
                if start_high:
                    self._signal.set(self._set_action(1))
                    await timer_high
                while True:
                    self._signal.set(self._set_action(0))
                    await timer_low
                    self._signal.set(self._set_action(1))
                    await timer_high

        self._task = cocotb.start_soon(drive())
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
        self._task.cancel()
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

    def __repr__(self) -> str:
        return self._repr

    @cached_property
    def _repr(self) -> str:
        freq_mhz = 1 / get_time_from_sim_steps(
            get_sim_steps(self._period, self._unit), "us"
        )
        return f"<{type(self).__qualname__}, {self._signal._path} @ {freq_mhz} MHz>"

    @cached_property
    def _log(self) -> Logger:
        return logging.getLogger(
            f"cocotb.{type(self).__qualname__}.{self._signal._name}"
        )
