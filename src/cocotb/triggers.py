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

import logging
import warnings
from abc import abstractmethod
from decimal import Decimal
from fractions import Fraction
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    ClassVar,
    Coroutine,
    Generator,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)

import cocotb.handle
import cocotb.task
from cocotb import simulator
from cocotb._deprecation import deprecated
from cocotb._outcomes import Error, Outcome, Value
from cocotb._py_compat import cached_property
from cocotb._utils import remove_traceback_frames, singleton
from cocotb.utils import get_sim_steps, get_time_from_sim_steps

T = TypeVar("T")


def _pointer_str(obj: object) -> str:
    """Get the memory address of *obj* as used in :meth:`object.__repr__`.

    This is equivalent to ``sprintf("%p", id(obj))``, but python does not
    support ``%p``.
    """
    full_repr = object.__repr__(obj)  # gives "<{type} object at {address}>"
    return full_repr.rsplit(" ", 1)[1][:-1]


Self = TypeVar("Self", bound="Trigger")


class Trigger(Awaitable["Trigger"]):
    """Base class to derive from."""

    def __init__(self) -> None:
        self._primed = False

    @cached_property
    def log(self) -> logging.Logger:
        """A :class:`logging.Logger` for the trigger."""
        return logging.getLogger(f"cocotb.{type(self).__qualname__}.0x{id(self):x}")

    def _prime(self, callback: Callable[["Trigger"], None]) -> None:
        """Set a callback to be invoked when the trigger fires.

        The callback will be invoked with a single argument, `self`.

        Sub-classes must override this, but should end by calling the base class
        method.

        .. warning::
            Do not call this directly within a :term:`task`. It is intended to be used
            only by the scheduler.
        """
        self._primed = True

    def _unprime(self) -> None:
        """Remove the callback, and perform cleanup if necessary.

        After being un-primed, a Trigger may be re-primed again in the future.
        Calling `_unprime` multiple times is allowed, subsequent calls should be
        a no-op.

        Sub-classes may override this, but should end by calling the base class
        method.

        .. warning::
            Do not call this directly within a :term:`task`. It is intended to be used
            only by the scheduler.
        """
        self._cleanup()

    def _cleanup(self) -> None:
        self._primed = False

    def __await__(self: Self) -> Generator[Self, None, Self]:
        yield self
        return self


class GPITrigger(Trigger):
    """Base Trigger class for GPI triggers.

    Consumes simulation time.
    """

    def __init__(self) -> None:
        super().__init__()

        # Required to ensure documentation can build
        # if simulator is not None:
        #    self.cbhdl = simulator.create_callback(self)
        # else:
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

        units: The unit of the time value.

            One of ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
            When *units* is ``'step'``,
            the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).

        round_mode:

            String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

    Raises:
        ValueError: If a non-positive value is passed for Timer setup.

    Usage:
        >>> await Timer(100, units="ps")

        The time can also be a ``float``:

        >>> await Timer(100e-9, units="sec")

        which is particularly convenient when working with frequencies:

        >>> freq = 10e6  # 10 MHz
        >>> await Timer(1 / freq, units="sec")

        Other built-in exact numeric types can be used too:

        >>> from fractions import Fraction
        >>> await Timer(Fraction(1, 10), units="ns")

        >>> from decimal import Decimal
        >>> await Timer(Decimal("100e-9"), units="sec")

        These are most useful when using computed durations while
        avoiding floating point inaccuracies.

    .. versionchanged:: 1.5
        Raise an exception when Timer uses a negative value as it is undefined behavior.
        Warn for 0 as this will cause erratic behavior in some simulators as well.

    .. versionchanged:: 1.5
        Support ``'step'`` as the *units* argument to mean "simulator time step".

    .. versionchanged:: 1.6
        Support rounding modes.

    .. versionremoved:: 2.0
        Passing ``None`` as the *units* argument was removed, use ``'step'`` instead.

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
        units: str = "step",
        *,
        round_mode: Optional[str] = None,
    ) -> None:
        super().__init__()
        if time <= 0:
            raise ValueError("Timer argument time must be positive")
        if round_mode is None:
            round_mode = type(self).round_mode
        self._sim_steps = get_sim_steps(time, units, round_mode=round_mode)
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
            get_time_from_sim_steps(self._sim_steps, units="ps"),
            _pointer_str(self),
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


_SignalType = TypeVar("_SignalType", bound="cocotb.handle.ValueObjectBase[Any, Any]")
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

    def __new__(cls, signal: "cocotb.handle.LogicObject") -> "RisingEdge":
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

    def __new__(cls, signal: "cocotb.handle.LogicObject") -> "FallingEdge":
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
        Prefer :attr:`await signal.value_change <cocotb.handle.NonArrayValueObject.rising_edge>` to ``await ValueChange(signal)``.

    .. versionadded: 2.0
    """

    _edge_type = simulator.VALUE_CHANGE

    def __new__(
        cls, signal: "cocotb.handle.NonArrayValueObject[Any, Any]"
    ) -> "ValueChange":
        if not isinstance(signal, cocotb.handle.NonArrayValueObject):
            raise TypeError(
                f"{cls.__qualname__} requires an object derived from NonArrayValueObject which can change value. Got {signal!r} of type {type(signal).__qualname__}"
            )
        return signal.value_change


@deprecated("Use `signal.value_change` instead.")
def Edge(signal: "cocotb.handle.NonArrayValueObject[Any, Any]") -> ValueChange:
    """Fires on any value change of *signal*.

    Args:
        signal: The signal upon which to wait for a value change.

    Raises:
        TypeError: If the signal is not an object which can change value.

    .. deprecated: 2.0

        Use :attr:`signal.value_change <cocotb.handle.NonArrayValueObject.value_change>` instead.
    """
    return ValueChange(signal)


class _Event(Trigger):
    """Unique instance used by the Event object.

    One created for each attempt to wait on the event so that the scheduler
    can maintain a unique mapping of triggers to tasks.
    """

    def __init__(self, parent: "Event") -> None:
        super().__init__()
        self._parent = parent

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._primed:
            return
        self._callback = callback
        self._parent._prime_trigger(self, callback)
        return super()._prime(callback)

    def _unprime(self) -> None:
        if not self._primed:
            return
        self._parent._unprime_trigger(self)
        return super()._unprime()

    def __repr__(self) -> str:
        return f"<{self._parent!r}.wait() at {_pointer_str(self)}>"


class Event:
    r"""A way to signal an event across :class:`~cocotb.task.Task`\ s.

    :keyword:`await`\ ing the result of :meth:`wait()` will block the :keyword:`await`\ ing :class:`~cocotb.task.Task`
    until :meth:`set` is called.

    Args:
        name: Name for the Event.

    Usage:
        .. code-block:: python

            e = Event()


            async def task1():
                await e.wait()
                print("resuming!")


            cocotb.start_soon(task1())
            # do stuff
            e.set()
            await NullTrigger()  # allows task1 to execute
            # resuming!

    .. versionremoved:: 2.0

        Removed the undocumented *data* attribute and argument to :meth:`set`.
    """

    def __init__(self, name: Optional[str] = None) -> None:
        self._pending_events: List[_Event] = []
        self.name: Optional[str] = name
        self._fired: bool = False
        self._data: Any = None

    @property
    @deprecated("The data field will be removed in a future release.")
    def data(self) -> Any:
        """The data associated with the Event.

        .. deprecated:: 2.0
            The data field will be removed in a future release.
            Use a separate variable to store the data instead.
        """
        return self._data

    @data.setter
    @deprecated("The data field will be removed in a future release.")
    def data(self, new_data: Any) -> None:
        self._data = new_data

    def _prime_trigger(
        self, trigger: _Event, callback: Callable[[Trigger], None]
    ) -> None:
        self._pending_events.append(trigger)

    def _unprime_trigger(self, trigger: _Event) -> None:
        self._pending_events.remove(trigger)

    def set(self, data: Optional[Any] = None) -> None:
        """Set the Event and unblock all Tasks blocked on this Event."""
        self._fired = True
        if data is not None:
            warnings.warn(
                "The data field will be removed in a future release.",
                DeprecationWarning,
            )
        self._data = data

        pending_events, self._pending_events = self._pending_events, []
        for event in pending_events:
            event._callback(event)

    def wait(self) -> Trigger:
        """Block the current Task until the Event is set.

        If the event has already been set, the trigger will fire immediately.

        To set the Event call :meth:`set`.
        To reset the Event (and enable the use of :meth:`wait` again),
        call :meth:`clear`.
        """
        if self._fired:
            return NullTrigger(name=f"{str(self)}.wait()")
        return _Event(self)

    def clear(self) -> None:
        """Clear this event that has been set.

        Subsequent calls to :meth:`~cocotb.triggers.Event.wait` will block until
        :meth:`~cocotb.triggers.Event.set` is called again.
        """
        self._fired = False

    def is_set(self) -> bool:
        """Return ``True`` if event has been set."""
        return self._fired

    def __repr__(self) -> str:
        if self.name is None:
            fmt = "<{0} at {2}>"
        else:
            fmt = "<{0} for {1} at {2}>"
        return fmt.format(type(self).__qualname__, self.name, _pointer_str(self))


class _InternalEvent(Trigger):
    """Event used internally for triggers that need cross-:class:`~cocotb.task.Task` synchronization.

    This Event can only be waited on once, by a single :class:`~cocotb.task.Task`.

    Provides transparent :func`repr` pass-through to the :class:`Trigger` using this event,
    providing a better debugging experience.
    """

    def __init__(self, parent: object) -> None:
        super().__init__()
        self._parent = parent
        self._callback: Optional[Callable[[Trigger], None]] = None
        self.fired: bool = False

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._callback is not None:
            raise RuntimeError("This Trigger may only be awaited once")
        self._callback = callback
        super()._prime(callback)
        if self.fired:
            self._callback(self)

    def set(self) -> None:
        """Wake up coroutine blocked on this event."""
        self.fired = True

        if self._callback is not None:
            self._callback(self)

    def is_set(self) -> bool:
        """Return true if event has been set."""
        return self.fired

    def __await__(
        self: Self,
    ) -> Generator[Any, Any, Self]:
        if self._primed:
            raise RuntimeError("Only one Task may await this Trigger")
        yield self
        return self

    def __repr__(self) -> str:
        return repr(self._parent)


class _Lock(Trigger):
    """Unique instance used by the Lock object.

    One created for each attempt to acquire the Lock so that the scheduler
    can maintain a unique mapping of triggers to tasks.
    """

    def __init__(self, parent: "Lock") -> None:
        super().__init__()
        self._parent = parent

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._primed:
            return
        self._callback = callback
        self._parent._prime_lock(self)
        return super()._prime(callback)

    def _unprime(self) -> None:
        if not self._primed:
            return
        self._parent._unprime_lock(self)
        return super()._unprime()

    def __repr__(self) -> str:
        return f"<{self._parent!r}.acquire() at {_pointer_str(self)}>"


class Lock(AsyncContextManager[None]):
    """A mutual exclusion lock (not re-entrant).

    Usage:
        By directly calling :meth:`acquire` and :meth:`release`.

        .. code-block:: python

            await lock.acquire()
            try:
                # do some stuff
            finally:
                lock.release()

        Or...

        .. code-block:: python

            async with lock:
                # do some stuff

    .. versionchanged:: 1.4

        The lock can be used as an asynchronous context manager in an
        :keyword:`async with` statement
    """

    def __init__(self, name: Optional[str] = None) -> None:
        self._pending_primed: List[_Lock] = []
        self.name: Optional[str] = name
        self._locked: bool = False

    def locked(self) -> bool:
        """Return ``True`` if the lock has been acquired.

        .. versionchanged:: 2.0
            This is now a method to match :meth:`asyncio.Lock.locked`, rather than an attribute.
        """
        return self._locked

    def _acquire_and_fire(self, lock: _Lock) -> None:
        self._locked = True
        lock._callback(lock)

    def _prime_lock(self, lock: _Lock) -> None:
        if not self._locked:
            self._acquire_and_fire(lock)
        else:
            self._pending_primed.append(lock)

    def _unprime_lock(self, lock: _Lock) -> None:
        if lock in self._pending_primed:
            self._pending_primed.remove(lock)

    def acquire(self) -> Trigger:
        """Produce a trigger which fires when the lock is acquired."""
        trig = _Lock(self)
        return trig

    def release(self) -> None:
        """Release the lock."""
        if not self._locked:
            raise RuntimeError(f"Attempt to release an unacquired Lock {str(self)}")

        self._locked = False

        # nobody waiting for this lock
        if not self._pending_primed:
            return

        lock = self._pending_primed.pop(0)
        self._acquire_and_fire(lock)

    def __repr__(self) -> str:
        if self.name is None:
            fmt = "<{0} [{2} waiting] at {3}>"
        else:
            fmt = "<{0} for {1} [{2} waiting] at {3}>"
        return fmt.format(
            type(self).__qualname__,
            self.name,
            len(self._pending_primed),
            _pointer_str(self),
        )

    async def __aenter__(self) -> None:
        await self.acquire()

    async def __aexit__(self, *args: Any) -> None:
        self.release()


class NullTrigger(Trigger):
    """Fires immediately.

    This is primarily for forcing the current Task to be rescheduled after all currently pending Tasks.

    .. versionremoved:: 2.0
        The *outcome* parameter was removed. There is no alternative.
    """

    def __init__(self, name: Optional[str] = None) -> None:
        super().__init__()
        self.name = name

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        callback(self)

    def __repr__(self) -> str:
        if self.name is None:
            fmt = "<{0} at {2}>"
        else:
            fmt = "<{0} for {1} at {2}>"
        return fmt.format(type(self).__qualname__, self.name, _pointer_str(self))


class TaskComplete(Trigger, Generic[T]):
    r"""Fires when a :class:`~cocotb.task.Task` completes.

    Unlike :func:`~cocotb.triggers.Join`, this Trigger does not return the result of the Task when :keyword:`await`\ ed.

    .. note::
        It is preferable to use :attr:`.Task.complete` to get this object over calling the constructor.

    .. code-block:: python

        async def coro_inner():
            await Timer(1, units="ns")
            raise ValueError("Oops")


        task = cocotb.start_soon(coro_inner())
        await task.complete  # no exception raised here
        assert task.exception() == ValueError("Oops")

    Args:
        task: The Task upon which to wait for completion.

    .. versionadded: 2.0
    """

    def __new__(cls, task: "cocotb.task.Task[T]") -> "TaskComplete[T]":
        return task.complete

    @classmethod
    def _make(cls, task: "cocotb.task.Task[T]") -> "TaskComplete[T]":
        self = super().__new__(cls)
        cls.__init__(self, task)
        return self

    def __init__(self, task: "cocotb.task.Task[T]") -> None:
        super().__init__()
        self._task = task

    def _prime(self, callback: Callable[[Trigger], None]) -> None:
        if self._task.done():
            callback(self)
        else:
            super()._prime(callback)

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._task!s})"

    @property
    def task(self) -> "cocotb.task.Task[T]":
        """The :class:`.Task` associated with this completion event."""
        return self._task


@deprecated(
    "Using `task` directly is prefered to `Join(task)` in all situations where the latter could be used."
)
def Join(task: "cocotb.task.Task[T]") -> "cocotb.task.Task[T]":
    r"""Fires when a :class:`~cocotb.task.Task` completes and returns the Task's result.

    Equivalent to calling :meth:`task.join() <cocotb.task.Task.join>`.

    .. code-block:: python

        async def coro_inner():
            await Timer(1, units="ns")
            return "Hello world"


        task = cocotb.start_soon(coro_inner())
        result = await Join(task)
        assert result == "Hello world"

    Args:
        task: The Task upon which to wait for completion.

    Returns:
        Object that can be :keyword:`await`\ ed or passed into :class:`~cocotb.triggers.First` or :class:`~cocotb.triggers.Combine`;
        the result of which will be the result of the Task.

    .. deprecated:: 2.0
        Using ``task`` directly is prefered to ``Join(task)`` in all situations where the latter could be used.
    """
    return task


class Waitable(Awaitable[T]):
    """Base class for trigger-like objects implemented using coroutines.

    This converts a ``_wait`` abstract method into a suitable ``__await__``.
    """

    @abstractmethod
    async def _wait(self) -> T:
        """The coroutine function which implements the functionality of the Waitable."""

    def __await__(self) -> Generator[Any, Any, T]:
        return self._wait().__await__()


class _AggregateWaitable(Waitable[T]):
    """Base class for :class:`Combine` and :class:`First`."""

    def __init__(
        self, *trigger: Union[Trigger, Waitable[Any], "cocotb.task.Task[Any]"]
    ) -> None:
        self._triggers = trigger

        # Do some basic type-checking up front, rather than waiting until we
        # await them.
        allowed_types = (Trigger, Waitable, cocotb.task.Task)
        for t in self._triggers:
            if not isinstance(t, allowed_types):
                raise TypeError(
                    f"All triggers must be instances of Trigger! Got: {type(t).__qualname__}"
                )

    def __repr__(self) -> str:
        # no _pointer_str here, since this is not a trigger, so identity
        # doesn't matter.
        return "{}({})".format(
            type(self).__qualname__,
            ", ".join(repr(t) for t in self._triggers),
        )


async def _wait_callback(
    trigger: Union[Trigger, Waitable[T], "cocotb.task.Task[T]"],
    callback: Callable[[Outcome[T]], None],
) -> None:
    """Wait for *trigger*, and call *callback* with the outcome of the await."""
    ret: Outcome[T]
    try:
        ret = Value(await trigger)  # type: ignore # awaiting trigger has a complicated type
    except BaseException as exc:
        # hide this from the traceback
        ret = Error(remove_traceback_frames(exc, ["_wait_callback"]))
    callback(ret)


class Combine(_AggregateWaitable["Combine"]):
    r"""Trigger that fires when all *triggers* have fired.

    :keyword:`await`\ ing this returns the :class:`Combine` object.
    This is similar to Verilog's ``join``.
    See :ref:`combine-tutorial` for an example.

    Args:
        trigger: One or more :keyword:`await`\ able objects.

    Raises:
        TypeError: When an unsupported *trigger* object is passed.
    """

    async def _wait(self) -> "Combine":
        if len(self._triggers) == 0:
            await NullTrigger()
        elif len(self._triggers) == 1:
            await self._triggers[0]
        else:
            waiters: List[cocotb.task.Task[Any]] = []
            e = _InternalEvent(self)
            triggers = list(self._triggers)

            # start a parallel task for each trigger
            for t in triggers:
                # t=t is needed for the closure to bind correctly
                def on_done(
                    ret: Outcome["Combine"],
                    t: Union[
                        Trigger, Waitable["Combine"], cocotb.task.Task["Combine"]
                    ] = t,
                ) -> None:
                    triggers.remove(t)
                    if not triggers:
                        e.set()
                    ret.get()  # re-raise any exception

                waiters.append(cocotb.start_soon(_wait_callback(t, on_done)))

            # wait for the last waiter to complete
            await e

        return self


class First(_AggregateWaitable[Any]):
    r"""Fires when the first trigger in *triggers* fires.

    :keyword:`await`\ ing this object returns the result of the first trigger that fires.
    This is similar to Verilog's ``join_any``.
    See :ref:`first-tutorial` for an example.

    Args:
        trigger: One or more :keyword:`await`\ able objects.

    Raises:
        TypeError: When an unsupported *trigger* object is passed.
        ValueError: When no triggers are passed.

    .. note::
        The event loop is single threaded, so while events may be simultaneous
        in simulation time, they can never be simultaneous in real time.
        For this reason, the value of ``t_ret is t1`` in the following example
        is implementation-defined, and will vary by simulator::

            t1 = Timer(10, units="ps")
            t2 = Timer(10, units="ps")
            t_ret = await First(t1, t2)

    .. note::
        In the old-style :ref:`generator-based coroutines <yield-syntax>`, ``t = yield [a, b]`` was another spelling of
        ``t = yield First(a, b)``. This spelling is no longer available when using :keyword:`await`-based
        coroutines.
    """

    def __init__(
        self, *trigger: Union[Trigger, Waitable[Any], "cocotb.task.Task[Any]"]
    ) -> None:
        if not trigger:
            raise ValueError("First() requires at least one Trigger or Task argument")
        super().__init__(*trigger)

    async def _wait(self) -> Any:
        if len(self._triggers) == 1:
            return await self._triggers[0]

        waiters: List[cocotb.task.Task[Any]] = []
        e = _InternalEvent(self)
        completed: List[Outcome[Any]] = []
        # start a parallel task for each trigger
        for t in self._triggers:

            def on_done(ret: Outcome[Any]) -> None:
                completed.append(ret)
                e.set()

            waiters.append(cocotb.start_soon(_wait_callback(t, on_done)))

        # wait for a waiter to complete
        await e

        # kill all the other waiters
        # TODO: Should this kill the coroutines behind any Join triggers?
        # Right now it does not.
        for w in waiters:
            w.kill()

        return completed[0].get()


class ClockCycles(Waitable["ClockCycles"]):
    r"""Finishes after *num_cycles* transitions of *signal*.

    :keyword:`await`\ ing this Trigger returns the ClockCycle object.

    Args:
        signal: The signal to monitor.
        num_cycles: The number of cycles to count.
        rising: If ``True``, count rising edges; if ``False``, count falling edges.
        edge: The kind of :ref:`edge-triggers` to count.

    .. warning::
        On many simulators transitions occur when the signal changes value from non-``0`` to ``0`` or non-``1`` to ``1``,
        not just from ``1`` to ``0`` or ``0`` to ``1``.

    .. versionadded:: 2.0
        Passing the edge trigger type: :class:`.RisingEdge`, :class:`.FallingEdge`, or :class:`.ValueChange`
        as the third positional argument or by the keyword *edge_type*.
    """

    @overload
    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
    ) -> None: ...

    @overload
    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
        _3: Union[bool, Type[RisingEdge], Type[FallingEdge], Type[ValueChange]],
    ) -> None: ...

    @overload
    def __init__(
        self, signal: "cocotb.handle.LogicObject", num_cycles: int, *, rising: bool
    ) -> None: ...

    @overload
    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
        *,
        edge_type: Union[Type[RisingEdge], Type[FallingEdge], Type[ValueChange]],
    ) -> None: ...

    def __init__(
        self,
        signal: "cocotb.handle.LogicObject",
        num_cycles: int,
        _3: Union[
            bool, Type[RisingEdge], Type[FallingEdge], Type[ValueChange], None
        ] = None,
        *,
        rising: Union[bool, None] = None,
        edge_type: Union[
            Type[RisingEdge], Type[FallingEdge], Type[ValueChange], None
        ] = None,
    ) -> None:
        self._signal = signal
        self._num_cycles = num_cycles
        self._edge_type: Union[Type[RisingEdge], Type[FallingEdge], Type[ValueChange]]
        if _3 is not None:
            if rising is not None or edge_type is not None:
                raise TypeError("Passed more than one edge selection argument.")
            if _3 is True:
                self._edge_type = RisingEdge
            elif _3 is False:
                self._edge_type = FallingEdge
            else:
                self._edge_type = _3
        elif rising is not None:
            if edge_type is not None:
                raise TypeError("Passed more than one edge selection argument.")
            self._edge_type = RisingEdge if rising else FallingEdge
        elif edge_type is not None:
            self._edge_type = edge_type
        else:
            # default if no argument is passed
            self._edge_type = RisingEdge

    @property
    def signal(self) -> "cocotb.handle.LogicObject":
        """The signal being monitored."""
        return self._signal

    @property
    def num_cycles(self) -> int:
        """The number of cycles to wait."""
        return self._num_cycles

    @property
    def edge_type(
        self,
    ) -> Union[Type[RisingEdge], Type[FallingEdge], Type[ValueChange]]:
        """The type of edge trigger used."""
        return self._edge_type

    async def _wait(self) -> "ClockCycles":
        trigger = self._edge_type(self._signal)
        for _ in range(self._num_cycles):
            await trigger
        return self

    def __repr__(self) -> str:
        return f"{type(self).__qualname__}({self._signal._path}, {self._num_cycles}, {self._edge_type.__qualname__})"


class SimTimeoutError(TimeoutError):
    """Exception thrown when a timeout, in terms of simulation time, occurs."""


@overload
async def with_timeout(
    trigger: Trigger,
    timeout_time: Union[float, Decimal],
    timeout_unit: str = "step",
    round_mode: Optional[str] = None,
) -> None: ...


@overload
async def with_timeout(
    trigger: Waitable[T],
    timeout_time: Union[float, Decimal],
    timeout_unit: str = "step",
    round_mode: Optional[str] = None,
) -> T: ...


@overload
async def with_timeout(
    trigger: "cocotb.task.Task[T]",
    timeout_time: Union[float, Decimal],
    timeout_unit: str = "step",
    round_mode: Optional[str] = None,
) -> T: ...


@overload
async def with_timeout(
    trigger: Coroutine[Any, Any, T],
    timeout_time: Union[float, Decimal],
    timeout_unit: str = "step",
    round_mode: Optional[str] = None,
) -> T: ...


async def with_timeout(
    trigger: Union[
        Trigger, Waitable[Any], "cocotb.task.Task[Any]", Coroutine[Any, Any, Any]
    ],
    timeout_time: Union[float, Decimal],
    timeout_unit: str = "step",
    round_mode: Optional[str] = None,
) -> Any:
    r"""Wait on triggers or coroutines, throw an exception if it waits longer than the given time.

    When a :term:`python:coroutine` is passed,
    the callee coroutine is started,
    the caller blocks until the callee completes,
    and the callee's result is returned to the caller.
    If timeout occurs, the callee is killed
    and :exc:`SimTimeoutError` is raised.

    When a :term:`task` is passed,
    the caller blocks until the callee completes
    and the callee's result is returned to the caller.
    If timeout occurs, the callee `continues to run`
    and :exc:`SimTimeoutError` is raised.

    If a :class:`~cocotb.triggers.Trigger` or :class:`~cocotb.triggers.Waitable` is passed,
    the caller blocks until the trigger fires,
    and the trigger is returned to the caller.
    If timeout occurs, the trigger is cancelled
    and :exc:`SimTimeoutError` is raised.

    Usage:
        .. code-block:: python

            await with_timeout(coro, 100, "ns")
            await with_timeout(First(coro, event.wait()), 100, "ns")

    Args:
        trigger:
            A single object that could be right of an :keyword:`await` expression in cocotb.
        timeout_time:
            Simulation time duration before timeout occurs.
        timeout_unit:
            Units of timeout_time, accepts any units that :class:`~cocotb.triggers.Timer` does.
        round_mode:
            String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

    Returns:
        First trigger that completed if timeout did not occur.

    Raises:
        :exc:`SimTimeoutError`: If timeout occurs.

    .. versionadded:: 1.3

    .. versionchanged:: 1.7
        Support passing :term:`python:coroutine`\ s.

    .. versionchanged:: 2.0
        Passing ``None`` as the *timeout_unit* argument was removed, use ``'step'`` instead.

    """
    if isinstance(trigger, Coroutine):
        trigger = cocotb.start_soon(trigger)
        shielded = False
    else:
        shielded = True
    timeout_timer = Timer(timeout_time, timeout_unit, round_mode=round_mode)
    res = await First(timeout_timer, trigger)
    if res is timeout_timer:
        if not shielded:
            # shielded = False only when trigger is a Task created to wrap a Coroutine
            trigger = cast(cocotb.task.Task[Any], trigger)
            trigger.kill()
        raise SimTimeoutError
    else:
        return res
