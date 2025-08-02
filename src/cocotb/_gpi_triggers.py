# Copyright cocotb contributors
# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""A collection of triggers which a testbench can :keyword:`await`."""

import warnings
from decimal import Decimal
from fractions import Fraction
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Generic,
    Optional,
    TypeVar,
    Union,
)

import cocotb
import cocotb.handle
from cocotb import simulator
from cocotb._base_triggers import Trigger
from cocotb._deprecation import deprecated
from cocotb._typing import RoundMode, TimeUnit
from cocotb._utils import pointer_str, singleton
from cocotb.utils import get_sim_steps, get_time_from_sim_steps

if TYPE_CHECKING:
    from cocotb._py_compat import Self


class GPITrigger(Trigger):
    """A trigger for a simulation event."""

    def __init__(self) -> None:
        super().__init__()
        self._cbhdl: Optional[simulator.gpi_cb_hdl] = None

    def _unprime(self) -> None:
        """Disable a primed trigger, can be re-primed."""
        if self._cbhdl is not None:
            self._cbhdl.deregister()
        return super()._unprime()

    def _cleanup(self) -> None:
        self._cbhdl = None
        return super()._cleanup()


class Timer(GPITrigger):
    r"""Fire after the specified simulation time period has elapsed.

    This trigger will *always* consume some simulation time
    and will return control to the :keyword:`await`\ ing task at the beginning of the time step.

    Args:
        time: The time value.

            .. versionchanged:: 1.5
                Previously this argument was misleadingly called `time_ps`.

        unit: The unit of the time value.

            One of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When *unit* is ``'step'``,
            the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).

            .. versionchanged:: 2.0
                Renamed from ``units``.

        round_mode:

            String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``, ``None``).
            A ``None`` argument is converted to the current value of :attr:`.Timer.round_mode`.

    Raises:
        ValueError: If a non-positive value is passed for Timer setup.

    Usage:
        >>> await Timer(100, unit="ps")

        The time can also be a ``float``:

        >>> await Timer(100e-9, unit="sec")

        which is particularly convenient when working with frequencies:

        >>> freq = 10e6  # 10 MHz
        >>> await Timer(1 / freq, unit="sec")

        Other built-in exact numeric types can be used too:

        >>> from fractions import Fraction
        >>> await Timer(Fraction(1, 10), unit="ns")

        >>> from decimal import Decimal
        >>> await Timer(Decimal("100e-9"), unit="sec")

        These are most useful when using computed durations while
        avoiding floating point inaccuracies.

    .. versionchanged:: 1.5
        Raise an exception when Timer uses a negative value as it is undefined behavior.
        Warn for 0 as this will cause erratic behavior in some simulators as well.

    .. versionchanged:: 1.5
        Support ``'step'`` as the *unit* argument to mean "simulator time step".

    .. versionchanged:: 1.6
        Support rounding modes.

    .. versionremoved:: 2.0
        Passing ``None`` as the *unit* argument was removed, use ``'step'`` instead.

    .. versionremoved:: 2.0
        The ``time_ps`` parameter was removed, use the ``time`` parameter instead.

    .. versionchanged:: 2.0
        Passing ``0`` as the *time* argument now raises a :exc:`ValueError`.
    """

    round_mode: ClassVar[RoundMode] = "error"
    """The default rounding mode."""

    def __init__(
        self,
        time: Union[float, Fraction, Decimal],
        unit: TimeUnit = "step",
        *,
        round_mode: Optional[RoundMode] = None,
        units: None = None,
    ) -> None:
        super().__init__()
        if time <= 0:
            raise ValueError("Timer argument time must be positive")
        if units is not None:
            warnings.warn(
                "The 'units' argument has been renamed to 'unit'.",
                DeprecationWarning,
                stacklevel=2,
            )
            unit = units
        if round_mode is None:
            round_mode = type(self).round_mode
        self._sim_steps = get_sim_steps(time, unit, round_mode=round_mode)
        # If we round to 0, we fix it up to 1 step as rounding is imprecise,
        # and Timer(0) is invalid.
        if self._sim_steps == 0:
            self._sim_steps = 1

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        """Register for a timed callback."""
        if self._cbhdl is None:
            self._cbhdl = simulator.register_timed_callback(
                self._sim_steps, callback, self
            )
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {self!s} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return "<{} of {:1.2f}ps at {}>".format(
            type(self).__qualname__,
            get_time_from_sim_steps(self._sim_steps, unit="ps"),
            pointer_str(self),
        )


@singleton
class ReadOnly(GPITrigger):
    """Fires when the current simulation timestep moves to the read-only phase.

    The read-only phase is entered when the current timestep no longer has any further delta steps.
    This will be a point where all the signal values are stable as there are no more RTL events scheduled for the timestep.
    The simulator will not allow scheduling of more events in this timestep.
    Useful for monitors which need to wait for all processes to execute (both RTL and cocotb) to ensure sampled signal values are final.
    """

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        if isinstance(current_gpi_trigger(), ReadOnly):
            raise RuntimeError(
                "Attempted illegal transition: awaiting ReadOnly in ReadOnly phase"
            )
        if self._cbhdl is None:
            self._cbhdl = simulator.register_readonly_callback(callback, self)
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {self!s} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}()"


@singleton
class ReadWrite(GPITrigger):
    """Fires when the read-write simulation phase is reached."""

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        if isinstance(current_gpi_trigger(), ReadOnly):
            raise RuntimeError(
                "Attempted illegal transition: awaiting ReadWrite in ReadOnly phase"
            )
        if self._cbhdl is None:
            self._cbhdl = simulator.register_rwsynch_callback(callback, self)
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {self!s} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}()"


@singleton
class NextTimeStep(GPITrigger):
    """Fires when the next time step is started."""

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        if self._cbhdl is None:
            self._cbhdl = simulator.register_nextstep_callback(callback, self)
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {self!s} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}()"


_SignalType = TypeVar("_SignalType", bound="cocotb.handle.ValueObjectBase[Any, Any]")


class _EdgeBase(GPITrigger, Generic[_SignalType]):
    """Internal base class that fires on a given edge of a signal."""

    _edge_type: ClassVar[int]
    signal: _SignalType

    @classmethod
    def _make(cls, signal: _SignalType) -> "Self":
        self = GPITrigger.__new__(cls)
        GPITrigger.__init__(self)
        self.signal = signal
        return self

    def __init__(self, _: _SignalType) -> None:
        pass

    def _prime(self, callback: Callable[["Self"], None]) -> None:
        if self._cbhdl is None:
            self._cbhdl = simulator.register_value_change_callback(
                self.signal._handle, callback, type(self)._edge_type, self
            )
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {self!s} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.signal!r})"


class RisingEdge(_EdgeBase["cocotb.handle.LogicObject"]):
    """Fires on the rising edge of *signal*, on a transition to ``1``.

    Only valid for scalar ``logic`` or ``bit``-typed signals.

    Args:
        signal: The signal upon which to wait for a rising edge.

    Raises:
        TypeError: If *signal* is not a 1-bit ``logic`` or ``bit``-typed object.

    .. note::
        Prefer :attr:`await signal.rising_edge <cocotb.handle.LogicObject.rising_edge>` to ``await RisingEdge(signal)``.

    .. warning::
        On many simulators this will trigger on transitions from non-``0``/``1`` value to ``1``,
        not just from ``0`` to ``1`` like the ``rising_edge`` function in VHDL.
    """

    _edge_type = simulator.RISING

    def __new__(cls, signal: "cocotb.handle.LogicObject") -> "RisingEdge":
        if not (isinstance(signal, cocotb.handle.LogicObject)):
            raise TypeError(
                f"{cls.__qualname__} requires a scalar LogicObject. Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal.rising_edge


class FallingEdge(_EdgeBase["cocotb.handle.LogicObject"]):
    """Fires on the falling edge of *signal*, on a transition to ``0``.

    Only valid for scalar ``logic`` or ``bit``-typed signals.

    Args:
        signal: The signal upon which to wait for a rising edge.

    Raises:
        TypeError: If *signal* is not a 1-bit ``logic`` or ``bit``-typed object.

    .. note::
        Prefer :attr:`await signal.falling_edge <cocotb.handle.LogicObject.falling_edge>` to ``await FallingEdge(signal)``.

    .. warning::
        On many simulators this will trigger on transitions from non-``0``/``1`` value to ``0``,
        not just from ``1`` to ``0`` like the ``falling_edge`` function in VHDL.
    """

    _edge_type = simulator.FALLING

    def __new__(cls, signal: "cocotb.handle.LogicObject") -> "FallingEdge":
        if not (isinstance(signal, cocotb.handle.LogicObject)):
            raise TypeError(
                f"{cls.__qualname__} requires a scalar LogicObject. Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal.falling_edge


class ValueChange(_EdgeBase["cocotb.handle._NonIndexableValueObjectBase[Any, Any]"]):
    """Fires on any value change of *signal*.

    Args:
        signal: The signal upon which to wait for a value change.

    Raises:
        TypeError: If the signal is not an object which can change value.

    .. note::
        Prefer :attr:`await signal.value_change <cocotb.handle.NonArrayValueObject.value_change>` to ``await ValueChange(signal)``.

    .. versionadded:: 2.0
    """

    _edge_type = simulator.VALUE_CHANGE

    def __new__(
        cls, signal: "cocotb.handle._NonIndexableValueObjectBase[Any, Any]"
    ) -> "ValueChange":
        if not isinstance(signal, cocotb.handle._NonIndexableValueObjectBase):
            raise TypeError(
                f"{cls.__qualname__} requires a simulation object derived from ValueObjectBase. "
                f"Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal.value_change


class Edge(ValueChange):
    """Fires on any value change of *signal*.

    Args:
        signal: The signal upon which to wait for a value change.

    Raises:
        TypeError: If the signal is not an object which can change value.

    .. deprecated:: 2.0

        Use :attr:`signal.value_change <cocotb.handle.NonArrayValueObject.value_change>` instead.
    """

    @deprecated("Use `signal.value_change` instead.")
    def __new__(
        cls, signal: "cocotb.handle._NonIndexableValueObjectBase[Any, Any]"
    ) -> "Edge":
        if not isinstance(signal, cocotb.handle._NonIndexableValueObjectBase):
            raise TypeError(
                f"{cls.__qualname__} requires a simulation object derived from ValueObjectBase. "
                f"Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal._edge


# The initializer is a lie, but a useful one. Perhaps one day this can be something like `StartupTrigger`.`
_current_gpi_trigger = Timer(1, "step")  # type: Union[None, GPITrigger]


def current_gpi_trigger() -> GPITrigger:
    """Return the last GPITrigger that fired."""
    if _current_gpi_trigger is None:
        raise RuntimeError("No GPI trigger has fired.")
    return _current_gpi_trigger
