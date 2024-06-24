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

"""A collections of triggers which a testbench can await."""

import abc
import functools
import inspect
import warnings
from collections.abc import Awaitable
from decimal import Decimal
from numbers import Real
from typing import Any, Callable, Coroutine, Optional, TypeVar, Union

import cocotb
from cocotb import outcomes, simulator
from cocotb._deprecation import deprecated
from cocotb.log import SimLog
from cocotb.task import Task
from cocotb.utils import (
    ParametrizedSingleton,
    get_sim_steps,
    get_time_from_sim_steps,
    lazy_property,
    remove_traceback_frames,
)

T = TypeVar("T")


def _pointer_str(obj):
    """
    Get the memory address of *obj* as used in :meth:`object.__repr__`.

    This is equivalent to ``sprintf("%p", id(obj))``, but python does not
    support ``%p``.
    """
    full_repr = object.__repr__(obj)  # gives "<{type} object at {address}>"
    return full_repr.rsplit(" ", 1)[1][:-1]


class TriggerException(Exception):
    pass


class Trigger(Awaitable):
    """Base class to derive from."""

    # __dict__ is needed here for the `.log` lazy_property below to work.
    # The implementation of `_PyObject_GenericGetAttrWithDict` suggests that
    # despite its inclusion, __slots__ will overall give speed and memory
    # improvements:
    #  - the `__dict__` is not actually constructed until it's needed, and that
    #    only happens if the `.log` attribute is used, where performance
    #    concerns no longer matter.
    #  - Attribute setting and getting will still go through the slot machinery
    #    first, as "data descriptors" take priority over dict access
    __slots__ = ("primed", "__weakref__", "__dict__")

    def __init__(self):
        self.primed = False

    @lazy_property
    def log(self):
        return SimLog("cocotb.%s" % (type(self).__qualname__), id(self))

    @abc.abstractmethod
    def prime(self, callback):
        """Set a callback to be invoked when the trigger fires.

        The callback will be invoked with a single argument, `self`.

        Sub-classes must override this, but should end by calling the base class
        method.

        .. warning::
            Do not call this directly within a :term:`task`. It is intended to be used
            only by the scheduler.
        """
        self.primed = True

    def unprime(self):
        """Remove the callback, and perform cleanup if necessary.

        After being un-primed, a Trigger may be re-primed again in the future.
        Calling `unprime` multiple times is allowed, subsequent calls should be
        a no-op.

        Sub-classes may override this, but should end by calling the base class
        method.

        .. warning::
            Do not call this directly within a :term:`task`. It is intended to be used
            only by the scheduler.
        """
        self.primed = False

    def __del__(self):
        # Ensure if a trigger drops out of scope we remove any pending callbacks
        self.unprime()

    @property
    def _outcome(self):
        """The result that `await this_trigger` produces in a coroutine.

        The default is to produce the trigger itself, which is done for
        ease of use with :class:`~cocotb.triggers.First`.
        """
        return outcomes.Value(self)

    def __await__(self):
        # hand the trigger back to the scheduler trampoline
        return (yield self)


class PythonTrigger(Trigger):
    """Python triggers don't use GPI at all.

    For example: notification of coroutine completion.
    """


class GPITrigger(Trigger):
    """Base Trigger class for GPI triggers.

    Consumes simulation time.
    """

    __slots__ = ("cbhdl",)

    def __init__(self):
        Trigger.__init__(self)

        # Required to ensure documentation can build
        # if simulator is not None:
        #    self.cbhdl = simulator.create_callback(self)
        # else:
        self.cbhdl = None

    def unprime(self):
        """Disable a primed trigger, can be re-primed."""
        if self.cbhdl is not None:
            self.cbhdl.deregister()
        self.cbhdl = None
        Trigger.unprime(self)


class Timer(GPITrigger):
    """Fire after the specified simulation time period has elapsed."""

    round_mode: str = "error"

    def __init__(
        self,
        time: Union[Real, Decimal] = None,
        units: str = "step",
        *,
        round_mode: Optional[str] = None,
        time_ps: Union[Real, Decimal] = None,
    ) -> None:
        """
        Args:
           time: The time value.

               .. versionchanged:: 1.5.0
                  Previously this argument was misleadingly called `time_ps`.

           units: One of
               ``'step'``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
               When *units* is ``'step'``,
               the timestep is determined by the simulator (see :make:var:`COCOTB_HDL_TIMEPRECISION`).

            round_mode (str, optional):
                String specifying how to handle time values that sit between time steps
                (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

        Examples:

            >>> await Timer(100, units='ps')

            The time can also be a ``float``:

            >>> await Timer(100e-9, units='sec')

            which is particularly convenient when working with frequencies:

            >>> freq = 10e6  # 10 MHz
            >>> await Timer(1 / freq, units='sec')

            Other builtin exact numeric types can be used too:

            >>> from fractions import Fraction
            >>> await Timer(Fraction(1, 10), units='ns')

            >>> from decimal import Decimal
            >>> await Timer(Decimal('100e-9'), units='sec')

            These are most useful when using computed durations while
            avoiding floating point inaccuracies.

        See Also:
            :func:`~cocotb.utils.get_sim_steps`

        Raises:
            TriggerException: If a negative value is passed for Timer setup.

        .. versionchanged:: 1.5
            Raise an exception when Timer uses a negative value as it is undefined behavior.
            Warn for 0 as this will cause erratic behavior in some simulators as well.

        .. versionchanged:: 1.5
            Support ``'step'`` as the *units* argument to mean "simulator time step".

        .. deprecated:: 1.5
            Using ``None`` as the *units* argument is deprecated, use ``'step'`` instead.

        .. versionchanged:: 1.6
            Support rounding modes.
        """
        GPITrigger.__init__(self)
        if time_ps is not None:
            if time is not None:
                raise TypeError(
                    "Gave argument to both the 'time' and deprecated 'time_ps' parameter"
                )
            time = time_ps
            warnings.warn(
                "The parameter name 'time_ps' has been renamed to 'time'. Please update your invocation.",
                DeprecationWarning,
                stacklevel=2,
            )
        else:
            if time is None:
                raise TypeError("Missing required argument 'time'")
        if time <= 0:
            if time == 0:
                warnings.warn(
                    "Timer setup with value 0, which might exhibit undefined behavior in some simulators",
                    category=RuntimeWarning,
                    stacklevel=2,
                )
            else:
                raise TriggerException("Timer value time_ps must not be negative")
        if units is None:
            warnings.warn(
                'Using units=None is deprecated, use units="step" instead.',
                DeprecationWarning,
                stacklevel=2,
            )
            units = "step"  # don't propagate deprecated value
        if round_mode is None:
            round_mode = type(self).round_mode
        self.sim_steps = get_sim_steps(time, units, round_mode=round_mode)

    def prime(self, callback):
        """Register for a timed callback."""
        if self.cbhdl is None:
            self.cbhdl = simulator.register_timed_callback(
                self.sim_steps, callback, self
            )
            if self.cbhdl is None:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __repr__(self):
        return "<{} of {:1.2f}ps at {}>".format(
            type(self).__qualname__,
            get_time_from_sim_steps(self.sim_steps, units="ps"),
            _pointer_str(self),
        )


# This is needed to make our custom metaclass work with abc.ABCMeta used in the
# `Trigger` base class.
class _ParameterizedSingletonAndABC(ParametrizedSingleton, abc.ABCMeta):
    pass


class ReadOnly(GPITrigger, metaclass=_ParameterizedSingletonAndABC):
    """Fires when the current simulation timestep moves to the read-only phase.

    The read-only phase is entered when the current timestep no longer has any further delta steps.
    This will be a point where all the signal values are stable as there are no more RTL events scheduled for the timestep.
    The simulator will not allow scheduling of more events in this timestep.
    Useful for monitors which need to wait for all processes to execute (both RTL and cocotb) to ensure sampled signal values are final.
    """

    __slots__ = ()

    @classmethod
    def __singleton_key__(cls):
        return None

    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        if self.cbhdl is None:
            self.cbhdl = simulator.register_readonly_callback(callback, self)
            if self.cbhdl is None:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __repr__(self):
        return "{}()".format(type(self).__qualname__)


class ReadWrite(GPITrigger, metaclass=_ParameterizedSingletonAndABC):
    """Fires when the read-write portion of the simulation cycles is reached."""

    __slots__ = ()

    @classmethod
    def __singleton_key__(cls):
        return None

    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        if self.cbhdl is None:
            self.cbhdl = simulator.register_rwsynch_callback(callback, self)
            if self.cbhdl is None:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __repr__(self):
        return "{}()".format(type(self).__qualname__)


class NextTimeStep(GPITrigger, metaclass=_ParameterizedSingletonAndABC):
    """Fires when the next time step is started."""

    __slots__ = ()

    @classmethod
    def __singleton_key__(cls):
        return None

    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        if self.cbhdl is None:
            self.cbhdl = simulator.register_nextstep_callback(callback, self)
            if self.cbhdl is None:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __repr__(self):
        return "{}()".format(type(self).__qualname__)


class _EdgeBase(GPITrigger, metaclass=_ParameterizedSingletonAndABC):
    """Internal base class that fires on a given edge of a signal."""

    __slots__ = ("signal",)

    @classmethod
    @property
    def _edge_type(self):
        """The edge type, as understood by the C code. Must be set in sub-classes."""
        raise NotImplementedError

    @classmethod
    def __singleton_key__(cls, signal):
        return signal

    def __init__(self, signal):
        super().__init__()
        self.signal = signal

    def prime(self, callback):
        """Register notification of a value change via a callback"""
        if self.cbhdl is None:
            self.cbhdl = simulator.register_value_change_callback(
                self.signal._handle, callback, type(self)._edge_type, self
            )
            if self.cbhdl is None:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        super().prime(callback)

    def __repr__(self):
        return "{}({!r})".format(type(self).__qualname__, self.signal)


class RisingEdge(_EdgeBase):
    """Fires on the rising edge of *signal*, on a transition from ``0`` to ``1``."""

    __slots__ = ()
    _edge_type = 1


class FallingEdge(_EdgeBase):
    """Fires on the falling edge of *signal*, on a transition from ``1`` to ``0``."""

    __slots__ = ()
    _edge_type = 2


class Edge(_EdgeBase):
    """Fires on any value change of *signal*."""

    __slots__ = ()
    _edge_type = 3


class _Event(PythonTrigger):
    """Unique instance used by the Event object.

    One created for each attempt to wait on the event so that the scheduler
    can maintain a dictionary of indexing each individual coroutine.

    FIXME: This will leak - need to use peers to ensure everything is removed
    """

    def __init__(self, parent):
        PythonTrigger.__init__(self)
        self.parent = parent

    def prime(self, callback):
        self._callback = callback
        self.parent._prime_trigger(self, callback)
        Trigger.prime(self, callback)

    def __call__(self):
        self._callback(self)

    def __repr__(self):
        return "<{!r}.wait() at {}>".format(self.parent, _pointer_str(self))


class Event:
    """Event to permit synchronization between two coroutines.

    Awaiting :meth:`wait()` from one coroutine will block the coroutine until
    :meth:`set()` is called somewhere else.
    """

    def __init__(self, name=None):
        self._pending = []
        self.name = name
        self._fired = False
        self.data = None

    @property
    @deprecated("The `.fired` attribute is deprecated, use `.is_set()` instead.")
    def fired(self) -> bool:
        return self._fired

    def _prime_trigger(self, trigger, callback):
        self._pending.append(trigger)

    def set(self, data=None):
        """Wake up all coroutines blocked on this event."""
        self._fired = True
        self.data = data

        p = self._pending[:]

        self._pending = []

        for trigger in p:
            trigger()

    def wait(self):
        """Get a trigger which fires when another coroutine sets the event.

        If the event has already been set, the trigger will fire immediately.

        To reset the event (and enable the use of ``wait`` again),
        :meth:`clear` should be called.
        """
        if self._fired:
            return NullTrigger(name=f"{str(self)}.wait()")
        return _Event(self)

    def clear(self):
        """Clear this event that has fired.

        Subsequent calls to :meth:`~cocotb.triggers.Event.wait` will block until
        :meth:`~cocotb.triggers.Event.set` is called again."""
        self._fired = False

    def is_set(self) -> bool:
        """Return ``True`` if event has been set."""
        return self._fired

    def __repr__(self):
        if self.name is None:
            fmt = "<{0} at {2}>"
        else:
            fmt = "<{0} for {1} at {2}>"
        return fmt.format(type(self).__qualname__, self.name, _pointer_str(self))


class _InternalEvent(PythonTrigger):
    """Event used internally for triggers that need cross-coroutine synchronization.

    This Event can only be waited on once, by a single coroutine.

    Provides transparent __repr__ pass-through to the Trigger using this event,
    providing a better debugging experience.
    """

    def __init__(self, parent):
        PythonTrigger.__init__(self)
        self.parent = parent
        self._callback = None
        self.fired = False
        self.data = None

    def prime(self, callback):
        if self._callback is not None:
            raise RuntimeError("This Trigger may only be awaited once")
        self._callback = callback
        Trigger.prime(self, callback)
        if self.fired:
            self._callback(self)

    def set(self, data=None):
        """Wake up coroutine blocked on this event."""
        self.fired = True
        self.data = data

        if self._callback is not None:
            self._callback(self)

    def is_set(self) -> bool:
        """Return true if event has been set."""
        return self.fired

    def __await__(self):
        if self.primed:
            raise RuntimeError("Only one coroutine may await this Trigger")
        # hand the trigger back to the scheduler trampoline
        return (yield self)

    def __repr__(self):
        return repr(self.parent)


class _Lock(PythonTrigger):
    """Unique instance used by the Lock object.

    One created for each attempt to acquire the Lock so that the scheduler
    can maintain a dictionary of indexing each individual coroutine.

    FIXME: This will leak - need to use peers to ensure everything is removed.
    """

    def __init__(self, parent):
        PythonTrigger.__init__(self)
        self.parent = parent

    def prime(self, callback):
        self._callback = callback
        self.parent._prime_trigger(self, callback)
        Trigger.prime(self, callback)

    def __call__(self):
        self._callback(self)

    def __repr__(self):
        return "<{!r}.acquire() at {}>".format(self.parent, _pointer_str(self))


_FT = TypeVar("_FT", bound=Callable)


def _locked_back_compat_dec(func: _FT) -> _FT:
    # this hack is implemented this way so that it is easy to delete later

    def get(inst, _=None):
        method = _LockBackCompat(inst, func)
        # cache bound method on object to override the descriptor
        setattr(inst, func.__name__, method)
        return method

    # Override the default function descriptor with one that returns a _LockBackCompat object that *acts* like a bound method,
    # but also defines the __bool__ overload that provides the deprecation warning.
    func.__get__ = get
    return func


class _LockBackCompat:
    def __init__(self, inst, func):
        self._inst = inst
        self._func = func
        functools.update_wrapper(self, func)

    def __call__(self):
        return self._func(self._inst)

    def __bool__(self):
        warnings.warn(
            f"Using `{self._func.__qualname__}` as a boolean attribute is deprecated. Call it as if it were a method instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._func(self._inst)


class Lock:
    """Lock primitive (not re-entrant).

    This can be used as::

        await lock.acquire()
        try:
            # do some stuff
        finally:
            lock.release()

    .. versionchanged:: 1.4

        The lock can be used as an asynchronous context manager in an
        :keyword:`async with` statement::

            async with lock:
                # do some stuff
    """

    def __init__(self, name=None):
        self._pending_unprimed = []
        self._pending_primed = []
        self.name = name
        self._locked = False

    @_locked_back_compat_dec
    def locked(self) -> bool:
        """Return ``True`` if the lock has been acquired.

        .. versionchanged:: 2.0
            This is now a method rather than an attribute, to match :meth:`asyncio.Lock.locked`.
        """
        return self._locked

    def _prime_trigger(self, trigger, callback):
        self._pending_unprimed.remove(trigger)

        if not self._locked:
            self._locked = True
            callback(trigger)
        else:
            self._pending_primed.append(trigger)

    def acquire(self):
        """Produce a trigger which fires when the lock is acquired."""
        trig = _Lock(self)
        self._pending_unprimed.append(trig)
        return trig

    def release(self):
        """Release the lock."""
        if not self._locked:
            raise TriggerException(
                "Attempt to release an unacquired Lock %s" % (str(self))
            )

        self._locked = False

        # nobody waiting for this lock
        if not self._pending_primed:
            return

        trigger = self._pending_primed.pop(0)
        self._locked = True
        trigger()

    def __repr__(self):
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

    @deprecated("`bool(lock)` is deprecated. Use the `.locked()` method instead.")
    def __bool__(self):
        """Provide boolean of a Lock"""
        return self._locked

    async def __aenter__(self):
        return await self.acquire()

    async def __aexit__(self, exc_type, exc, tb):
        self.release()


class NullTrigger(Trigger):
    """Fires immediately.

    Primarily for internal scheduler use.
    """

    def __init__(self, name=None, outcome=None, _outcome=None):
        super().__init__()
        self._callback = None
        self.name = name
        if outcome is not None:
            warnings.warn(
                "Passing the `outcome` argument and having that be the result of the `await` expression on this Trigger is deprecated.",
                DeprecationWarning,
                stacklevel=2,
            )
        self.__outcome = _outcome if _outcome is not None else outcome

    @property
    def _outcome(self):
        if self.__outcome is not None:
            return self.__outcome
        return super()._outcome

    def prime(self, callback):
        callback(self)

    def __repr__(self):
        if self.name is None:
            fmt = "<{0} at {2}>"
        else:
            fmt = "<{0} for {1} at {2}>"
        return fmt.format(type(self).__qualname__, self.name, _pointer_str(self))


class Join(PythonTrigger, metaclass=_ParameterizedSingletonAndABC):
    r"""Fires when a task completes.

    The result of blocking on the trigger can be used to get the coroutine
    result::

        async def coro_inner():
            await Timer(1, units='ns')
            return "Hello world"

        task = cocotb.start_soon(coro_inner())
        result = await Join(task)
        assert result == "Hello world"

    If the coroutine threw an exception, the :keyword:`await` will re-raise it.

    """

    __slots__ = ("_coroutine",)

    @classmethod
    def __singleton_key__(cls, coroutine):
        return coroutine

    def __init__(self, coroutine):
        super().__init__()
        self._coroutine = coroutine

    @property
    def _outcome(self):
        outcome = self._coroutine._outcome
        if type(self._coroutine) is Task and isinstance(outcome, outcomes.Error):
            warnings.warn(
                "Tasks started with `cocotb.start_soon()` that raise Exceptions will not propagate those Exceptions in 2.0. "
                "Instead such Tasks will *always* fail the test. "
                "An alternative for `cocotb.start_soon()` that *always* propagates Exceptions will be added in 2.0.",
                FutureWarning,
            )
        return outcome

    @property
    @deprecated("Use `task.result()` to get the result of a joined Task.")
    def retval(self):
        """The return value of the joined coroutine.

        .. deprecated:: 1.9

            Use :meth:`Task.result() <cocotb.task.Task.result` to get the result of a joined Task.

            .. code-block: python3

                forked = cocotb.start_soon(mycoro())
                await forked.join()
                result = forked.result()
        """
        return self._coroutine.result()

    def prime(self, callback):
        if self._coroutine.done():
            callback(self)
        else:
            super().prime(callback)

    def __repr__(self):
        return "{}({!s})".format(type(self).__qualname__, self._coroutine)

    def __await__(self):
        warnings.warn(
            "`await`ing a Join trigger will return the Join trigger and not the result of the joined Task in 2.0.",
            FutureWarning,
            stacklevel=2,
        )
        return (yield self)


class Waitable(Awaitable):
    """
    Base class for trigger-like objects implemented using coroutines.

    This converts a `_wait` abstract method into a suitable `__await__`.
    """

    __slots__ = ()

    async def _wait(self):
        """
        Should be implemented by the sub-class. Called by `await self` to
        convert the waitable object into a coroutine.
        """
        raise NotImplementedError

    def __await__(self):
        return self._wait().__await__()


class _AggregateWaitable(Waitable):
    """
    Base class for Waitables that take mutiple triggers in their constructor
    """

    __slots__ = ("triggers",)

    def __init__(self, *triggers):
        self.triggers = triggers

        # Do some basic type-checking up front, rather than waiting until we
        # await them.
        allowed_types = (Trigger, Waitable, Task)
        for trigger in self.triggers:
            if not isinstance(trigger, allowed_types):
                raise TypeError(
                    "All triggers must be instances of Trigger! Got: {}".format(
                        type(trigger).__qualname__
                    )
                )

    def __repr__(self):
        # no _pointer_str here, since this is not a trigger, so identity
        # doesn't matter.
        return "{}({})".format(
            type(self).__qualname__,
            ", ".join(
                repr(Join(t)) if isinstance(t, Task) else repr(t) for t in self.triggers
            ),
        )


async def _wait_callback(trigger, callback):
    """
    Wait for a trigger, and call `callback` with the outcome of the await.
    """
    try:
        ret = outcomes.Value(await trigger)
    except BaseException as exc:
        # hide this from the traceback
        ret = outcomes.Error(remove_traceback_frames(exc, ["_wait_callback"]))
    callback(ret)


class Combine(_AggregateWaitable):
    """
    Fires when all of *triggers* have fired.

    Like most triggers, this simply returns itself.

    This is similar to Verilog's ``join``.
    """

    __slots__ = ()

    async def _wait(self):
        waiters = []
        e = _InternalEvent(self)
        triggers = list(self.triggers)

        # start a parallel task for each trigger
        for t in triggers:
            # t=t is needed for the closure to bind correctly
            def on_done(ret, t=t):
                triggers.remove(t)
                if not triggers:
                    e.set()
                ret.get()  # re-raise any exception

            waiters.append(cocotb.start_soon(_wait_callback(t, on_done)))

        # wait for the last waiter to complete
        await e
        return self


class First(_AggregateWaitable):
    """
    Fires when the first trigger in *triggers* fires.

    Returns the result of the trigger that fired.

    This is similar to Verilog's ``join_any``.

    .. note::
        The event loop is single threaded, so while events may be simultaneous
        in simulation time, they can never be simultaneous in real time.
        For this reason, the value of ``t_ret is t1`` in the following example
        is implementation-defined, and will vary by simulator::

            t1 = Timer(10, units='ps')
            t2 = Timer(10, units='ps')
            t_ret = await First(t1, t2)

    .. note::
        In the old-style :ref:`generator-based coroutines <yield-syntax>`, ``t = yield [a, b]`` was another spelling of
        ``t = yield First(a, b)``. This spelling is no longer available when using :keyword:`await`-based
        coroutines.
    """

    __slots__ = ()

    async def _wait(self):
        waiters = []
        e = _InternalEvent(self)
        completed = []
        # start a parallel task for each trigger
        for t in self.triggers:

            def on_done(ret):
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

        # These lines are the way they are to make tracebacks readable:
        #  - The comment helps the user understand why they are seeing the
        #    traceback, even if it is obvious top cocotb maintainers.
        #  - Using `NullTrigger` here instead of `result = completed[0].get()`
        #    means we avoid inserting an `outcome.get` frame in the traceback
        first_trigger = NullTrigger(_outcome=completed[0])
        return await first_trigger  # the first of multiple triggers that fired


class ClockCycles(Waitable):
    """Fires after *num_cycles* transitions of *signal* from ``0`` to ``1``."""

    def __init__(self, signal, num_cycles, rising=True):
        """
        Args:
            signal: The signal to monitor.
            num_cycles (int): The number of cycles to count.
            rising (bool, optional): If ``True``, the default, count rising edges.
                Otherwise, count falling edges.
        """
        self.signal = signal
        self.num_cycles = num_cycles
        if rising is True:
            self._type = RisingEdge
        else:
            self._type = FallingEdge

    async def _wait(self):
        trigger = self._type(self.signal)
        for _ in range(self.num_cycles):
            await trigger
        return self

    def __repr__(self):
        # no _pointer_str here, since this is not a trigger, so identity
        # doesn't matter.
        if self._type is RisingEdge:
            fmt = "{}({!r}, {!r})"
        else:
            fmt = "{}({!r}, {!r}, rising=False)"
        return fmt.format(type(self).__qualname__, self.signal, self.num_cycles)


async def with_timeout(
    trigger: Union[Trigger, Waitable, Task, Coroutine[Any, Any, T]],
    timeout_time: Union[float, Decimal],
    timeout_unit: str = "step",
    round_mode: Optional[str] = None,
) -> T:
    r"""
    Waits on triggers or coroutines, throws an exception if it waits longer than the given time.

    When a :term:`python:coroutine` is passed,
    the callee coroutine is started,
    the caller blocks until the callee completes,
    and the callee's result is returned to the caller.
    If timeout occurs, the callee is killed
    and :exc:`SimTimeoutError` is raised.

    When an unstarted :class:`~cocotb.coroutine`\ is passed,
    the callee coroutine is started,
    the caller blocks until the callee completes,
    and the callee's result is returned to the caller.
    If timeout occurs, the callee `continues to run`
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

        await with_timeout(coro, 100, 'ns')
        await with_timeout(First(coro, event.wait()), 100, 'ns')

    Args:
        trigger (:class:`~cocotb.triggers.Trigger`, :class:`~cocotb.triggers.Waitable`, :class:`~cocotb.task.Task`, or :term:`python:coroutine`):
            A single object that could be right of an :keyword:`await` expression in cocotb.
        timeout_time (numbers.Real or decimal.Decimal):
            Simulation time duration before timeout occurs.
        timeout_unit (str, optional):
            Units of timeout_time, accepts any units that :class:`~cocotb.triggers.Timer` does.
        round_mode (str, optional):
            String specifying how to handle time values that sit between time steps
            (one of ``'error'``, ``'round'``, ``'ceil'``, ``'floor'``).

    Returns:
        First trigger that completed if timeout did not occur.

    Raises:
        :exc:`SimTimeoutError`: If timeout occurs.

    .. versionadded:: 1.3

    .. deprecated:: 1.5
        Using ``None`` as the *timeout_unit* argument is deprecated, use ``'step'`` instead.

    .. versionchanged:: 1.7.0
        Support passing :term:`python:coroutine`\ s.
    """
    if timeout_unit is None:
        warnings.warn(
            'Using timeout_unit=None is deprecated, use timeout_unit="step" instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        timeout_unit = "step"  # don't propagate deprecated value
    if inspect.iscoroutine(trigger):
        trigger = cocotb.start_soon(trigger)
        shielded = False
    else:
        shielded = True
    timeout_timer = cocotb.triggers.Timer(
        timeout_time, timeout_unit, round_mode=round_mode
    )
    res = await First(timeout_timer, trigger)
    if res is timeout_timer:
        if not shielded:
            trigger.kill()
        raise cocotb.result.SimTimeoutError
    else:
        return res
