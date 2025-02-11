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

"""A collection of triggers which a testbench can :keyword:`await`."""

from decimal import Decimal
from fractions import Fraction
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
)

import cocotb
import cocotb.handle
from cocotb import simulator
from cocotb._base_triggers import Trigger
from cocotb._deprecation import deprecated
from cocotb._utils import pointer_str, singleton
from cocotb.utils import get_sim_steps, get_time_from_sim_steps

if TYPE_CHECKING:
    from cocotb.handle import LogicObject, NonArrayValueObject, ValueObjectBase


class GPITrigger(Trigger):
    """Base Trigger class for GPI triggers.

    Consumes simulation time.
    """

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
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

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

    round_mode: str = "error"
    """The default rounding mode."""

    def __init__(
        self,
        time: Union[float, Fraction, Decimal],
        unit: str = "step",
        *,
        round_mode: Optional[str] = None,
    ) -> None:
        super().__init__()
        if time <= 0:
            raise ValueError("Timer argument time must be positive")
        if round_mode is None:
            round_mode = type(self).round_mode
        self._sim_steps = get_sim_steps(time, unit, round_mode=round_mode)
        # If we round to 0, we fix it up to 1 step as rounding is imprecise,
        # and Timer(0) is invalid.
        if self._sim_steps == 0:
            self._sim_steps = 1

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        """Register for a timed callback."""
        if self._cbhdl is None:
            self._cbhdl = simulator.register_timed_callback(
                self._sim_steps, callback, self
            )
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {str(self)} Trigger")
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

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if cocotb.sim_phase is cocotb.SimPhase.READ_ONLY:
            raise RuntimeError(
                "Attempted illegal transition: awaiting ReadOnly in ReadOnly phase"
            )
        if self._cbhdl is None:
            self._cbhdl = simulator.register_readonly_callback(callback, self)
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {str(self)} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}()"


@singleton
class ReadWrite(GPITrigger):
    """Fires when the read-write simulation phase is reached."""

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if cocotb.sim_phase is cocotb.SimPhase.READ_ONLY:
            raise RuntimeError(
                "Attempted illegal transition: awaiting ReadWrite in ReadOnly phase"
            )
        if self._cbhdl is None:
            self._cbhdl = simulator.register_rwsynch_callback(callback, self)
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {str(self)} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}()"


@singleton
class NextTimeStep(GPITrigger):
    """Fires when the next time step is started."""

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._cbhdl is None:
            self._cbhdl = simulator.register_nextstep_callback(callback, self)
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {str(self)} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}()"


_SignalType = TypeVar("_SignalType", bound="ValueObjectBase[Any, Any]")
_EdgeBaseSelf = TypeVar("_EdgeBaseSelf", bound="_EdgeBase")


class _EdgeBase(GPITrigger, Generic[_SignalType]):
    """Internal base class that fires on a given edge of a signal."""

    _edge_type: ClassVar[int]
    signal: _SignalType

    @classmethod
    def _make(cls: Type[_EdgeBaseSelf], signal: _SignalType) -> _EdgeBaseSelf:
        self = GPITrigger.__new__(cls)
        GPITrigger.__init__(self)
        self.signal = signal
        return self

    def __init__(self, _: _SignalType) -> None:
        pass

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._cbhdl is None:
            self._cbhdl = simulator.register_value_change_callback(
                self.signal._handle, callback, type(self)._edge_type, self
            )
            if self._cbhdl is None:
                raise RuntimeError(f"Unable set up {str(self)} Trigger")
        super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self.signal!r})"


class RisingEdge(_EdgeBase):
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

    def __new__(cls, signal: "LogicObject") -> "RisingEdge":
        if not (isinstance(signal, cocotb.handle.LogicObject)):
            raise TypeError(
                f"{cls.__qualname__} requires a scalar LogicObject. Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal.rising_edge


class FallingEdge(_EdgeBase):
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

    def __new__(cls, signal: "LogicObject") -> "FallingEdge":
        if not (isinstance(signal, cocotb.handle.LogicObject)):
            raise TypeError(
                f"{cls.__qualname__} requires a scalar LogicObject. Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal.falling_edge


class ValueChange(_EdgeBase):
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

    def __new__(cls, signal: "NonArrayValueObject[Any, Any]") -> "ValueChange":
        if not isinstance(signal, cocotb.handle.NonArrayValueObject):
            raise TypeError(
                f"{cls.__qualname__} requires an object derived from NonArrayValueObject which can change value. Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal.value_change


@deprecated("Use `signal.value_change` instead.")
def Edge(signal: "NonArrayValueObject[Any, Any]") -> ValueChange:
    """Fires on any value change of *signal*.

    Args:
        signal: The signal upon which to wait for a value change.

    Raises:
        TypeError: If the signal is not an object which can change value.

    .. deprecated:: 2.0

        Use :attr:`signal.value_change <cocotb.handle.NonArrayValueObject.value_change>` instead.
    """
    return ValueChange(signal)
