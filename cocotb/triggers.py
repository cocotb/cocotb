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

"""A collections of triggers which a testbench can yield."""

import os
import sys
import textwrap
import abc

if "COCOTB_SIM" in os.environ:
    import simulator
else:
    simulator = None

from cocotb.log import SimLog
from cocotb.result import ReturnValue
from cocotb.utils import (
    get_sim_steps, get_time_from_sim_steps, ParametrizedSingleton,
    lazy_property,
)
from cocotb import decorators
from cocotb import outcomes
from cocotb import _py_compat
import cocotb


class TriggerException(Exception):
    pass

class Trigger(_py_compat.with_metaclass(abc.ABCMeta)):
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
    __slots__ = ('primed', '__weakref__', '__dict__')

    def __init__(self):
        self.primed = False

    @lazy_property
    def log(self):
        return SimLog("cocotb.%s" % (self.__class__.__name__), id(self))

    @abc.abstractmethod
    def prime(self, callback):
        """Set a callback to be invoked when the trigger fires.

        The callback will be invoked with a single argument, `self`.

        Sub-classes must override this, but should end by calling the base class
        method.

        Do not call this directly within coroutines, it is intended to be used
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

        Do not call this directly within coroutines, it is intended to be used
        only by the scheduler.
        """
        self.primed = False

    def __del__(self):
        # Ensure if a trigger drops out of scope we remove any pending callbacks
        self.unprime()

    def __str__(self):
        return self.__class__.__name__

    @property
    def _outcome(self):
        """The result that `yield this_trigger` produces in a coroutine.

        The default is to produce the trigger itself, which is done for
        ease of use with :class:`~cocotb.triggers.First`.
        """
        return outcomes.Value(self)

    # Once Python 2.7 support is dropped, this can be run unconditionally
    if sys.version_info >= (3, 3):
        _py_compat.exec_(textwrap.dedent("""
        def __await__(self):
            # hand the trigger back to the scheduler trampoline
            return (yield self)
        """))


class PythonTrigger(Trigger):
    """Python triggers don't use GPI at all.

    For example: notification of coroutine completion.
    """


class GPITrigger(Trigger):
    """Base Trigger class for GPI triggers.

    Consumes simulation time.
    """
    __slots__ = ('cbhdl',)

    def __init__(self):
        Trigger.__init__(self)

        # Required to ensure documentation can build
        # if simulator is not None:
        #    self.cbhdl = simulator.create_callback(self)
        # else:
        self.cbhdl = 0

    def unprime(self):
        """Disable a primed trigger, can be re-primed."""
        if self.cbhdl != 0:
            simulator.deregister_callback(self.cbhdl)
        self.cbhdl = 0
        Trigger.unprime(self)


class Timer(GPITrigger):
    """Fires after the specified simulation time period has elapsed."""
    def __init__(self, time_ps, units=None):
        """
        Args:
           time_ps (numbers.Real or decimal.Decimal): The time value.
               Note that despite the name this is not actually in picoseconds
               but depends on the *units* argument.
           units (str or None, optional): One of
               ``None``, ``'fs'``, ``'ps'``, ``'ns'``, ``'us'``, ``'ms'``, ``'sec'``.
               When no *units* is given (``None``) the timestep is determined by
               the simulator.

        Examples:

            >>> yield Timer(100, units='ps')

            The time can also be a ``float``:

            >>> yield Timer(100e-9, units='sec')

            which is particularly convenient when working with frequencies:

            >>> freq = 10e6  # 10 MHz
            >>> yield Timer(1 / freq, units='sec')

            Other builtin exact numeric types can be used too:

            >>> from fractions import Fraction
            >>> yield Timer(Fraction(1, 10), units='ns')

            >>> from decimal import Decimal
            >>> yield Timer(Decimal('100e-9'), units='sec')

            These are most useful when using computed durations while
            avoiding floating point inaccuracies.

        See Also:
            :func:`~cocotb.utils.get_sim_steps`
        """
        GPITrigger.__init__(self)
        self.sim_steps = get_sim_steps(time_ps, units)

    def prime(self, callback):
        """Register for a timed callback."""
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_timed_callback(self.sim_steps,
                                                           callback, self)
            if self.cbhdl == 0:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __str__(self):
        return self.__class__.__name__ + "(%1.2fps)" % get_time_from_sim_steps(self.sim_steps, units='ps')


# This is needed to make our custom metaclass work with abc.ABCMeta used in the
# `Trigger` base class.
class _ParameterizedSingletonAndABC(ParametrizedSingleton, abc.ABCMeta):
    pass


class ReadOnly(_py_compat.with_metaclass(_ParameterizedSingletonAndABC, GPITrigger)):
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
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_readonly_callback(callback, self)
            if self.cbhdl == 0:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __str__(self):
        return self.__class__.__name__ + "(readonly)"


class ReadWrite(_py_compat.with_metaclass(_ParameterizedSingletonAndABC, GPITrigger)):
    """Fires when the read-write portion of the sim cycles is reached."""
    __slots__ = ()

    @classmethod
    def __singleton_key__(cls):
        return None

    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        if self.cbhdl == 0:
            # import pdb
            # pdb.set_trace()
            self.cbhdl = simulator.register_rwsynch_callback(callback, self)
            if self.cbhdl == 0:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __str__(self):
        return self.__class__.__name__ + "(readwritesync)"


class NextTimeStep(_py_compat.with_metaclass(_ParameterizedSingletonAndABC, GPITrigger)):
    """Fires when the next time step is started."""
    __slots__ = ()

    @classmethod
    def __singleton_key__(cls):
        return None

    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_nextstep_callback(callback, self)
            if self.cbhdl == 0:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        GPITrigger.prime(self, callback)

    def __str__(self):
        return self.__class__.__name__ + "(nexttimestep)"


class _EdgeBase(_py_compat.with_metaclass(_ParameterizedSingletonAndABC, GPITrigger)):
    """Internal base class that fires on a given edge of a signal."""
    __slots__ = ('signal',)

    @classmethod
    @property
    def _edge_type(self):
        """The edge type, as understood by the C code. Must be set in sub-classes."""
        raise NotImplementedError

    @classmethod
    def __singleton_key__(cls, signal):
        return signal

    def __init__(self, signal):
        super(_EdgeBase, self).__init__()
        self.signal = signal

    def prime(self, callback):
        """Register notification of a value change via a callback"""
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_value_change_callback(
                self.signal._handle, callback, type(self)._edge_type, self
            )
            if self.cbhdl == 0:
                raise TriggerException("Unable set up %s Trigger" % (str(self)))
        super(_EdgeBase, self).prime(callback)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal._name


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


class Event(object):
    """Event to permit synchronization between two coroutines.

    Yielding :meth:`wait()` from one coroutine will block the coroutine until
    :meth:`set()` is called somewhere else.
    """

    def __init__(self, name=""):
        self._pending = []
        self.name = name
        self.fired = False
        self.data = None

    def _prime_trigger(self, trigger, callback):
        self._pending.append(trigger)

    def set(self, data=None):
        """Wake up all coroutines blocked on this event."""
        self.fired = True
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
        if self.fired:
            return NullTrigger(name="{}.wait()".format(str(self)))
        return _Event(self)

    def clear(self):
        """Clear this event that has fired.

        Subsequent calls to :meth:`~cocotb.triggers.Event.wait` will block until
        :meth:`~cocotb.triggers.Event.set` is called again."""
        self.fired = False

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.name


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


class Lock(object):
    """Lock primitive (not re-entrant).

    This should be used as::

        yield lock.acquire()
        try:
            # do some stuff
        finally:
            lock.release()
    """

    def __init__(self, name=""):
        self._pending_unprimed = []
        self._pending_primed = []
        self.name = name
        self.locked = False  #: ``True`` if the lock is held.

    def _prime_trigger(self, trigger, callback):
        self._pending_unprimed.remove(trigger)

        if not self.locked:
            self.locked = True
            callback(trigger)
        else:
            self._pending_primed.append(trigger)

    def acquire(self):
        """ Produce a trigger which fires when the lock is acquired. """
        trig = _Lock(self)
        self._pending_unprimed.append(trig)
        return trig

    def release(self):
        """Release the lock."""
        if not self.locked:
            raise TriggerException("Attempt to release an unacquired Lock %s" %
                        (str(self)))

        self.locked = False

        # nobody waiting for this lock
        if not self._pending_primed:
            return

        trigger = self._pending_primed.pop(0)
        self.locked = True
        trigger()

    def __str__(self):
        return "%s(%s) [%s waiting]" % (str(self.__class__.__name__),
                                        self.name,
                                        len(self._pending_primed))

    def __nonzero__(self):
        """Provide boolean of a Lock"""
        return self.locked

    __bool__ = __nonzero__


class NullTrigger(Trigger):
    """Fires immediately.

    Primarily for internal scheduler use.
    """
    def __init__(self, name="", outcome=None):
        super(NullTrigger, self).__init__()
        self._callback = None
        self.name = name
        self.__outcome = outcome

    @property
    def _outcome(self):
        if self.__outcome is not None:
            return self.__outcome
        return super(NullTrigger, self)._outcome

    def prime(self, callback):
        callback(self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.name


class Join(_py_compat.with_metaclass(_ParameterizedSingletonAndABC, PythonTrigger)):
    r"""Fires when a :func:`~cocotb.fork`\ ed coroutine completes.

    The result of blocking on the trigger can be used to get the coroutine
    result::

        @cocotb.coroutine()
        def coro_inner():
            yield Timer(1, units='ns')
            raise ReturnValue("Hello world")

        task = cocotb.fork(coro_inner())
        result = yield Join(task)
        assert result == "Hello world"

    Or using the syntax in Python 3.5 onwards:

    .. code-block:: python3

        @cocotb.coroutine()
        async def coro_inner():
            await Timer(1, units='ns')
            return "Hello world"

        task = cocotb.fork(coro_inner())
        result = await Join(task)
        assert result == "Hello world"

    If the coroutine threw an exception, the :keyword:`await` or :keyword:`yield`
    will re-raise it.

    """
    __slots__ = ('_coroutine',)

    @classmethod
    def __singleton_key__(cls, coroutine):
        return coroutine

    def __init__(self, coroutine):
        super(Join, self).__init__()
        self._coroutine = coroutine

    @property
    def _outcome(self):
        return self._coroutine._outcome

    @property
    def retval(self):
        """The return value of the joined coroutine.

        .. note::
            Typically there is no need to use this attribute - the
            following code samples are equivalent::

                forked = cocotb.fork(mycoro())
                j = Join(forked)
                yield j
                result = j.retval

            ::

                forked = cocotb.fork(mycoro())
                result = yield Join(forked)
        """
        return self._coroutine.retval

    def prime(self, callback):
        if self._coroutine._finished:
            callback(self)
        else:
            super(Join, self).prime(callback)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self._coroutine.__name__


class Waitable(object):
    """
    Compatibility layer that emulates `collections.abc.Awaitable`.

    This converts a `_wait` abstract method into a suitable `__await__` on
    supporting Python versions (>=3.3).
    """
    __slots__ = ()
    @decorators.coroutine
    def _wait(self):
        """
        Should be implemented by the sub-class. Called by `yield self` to
        convert the waitable object into a coroutine.

        ReturnValue can be used here.
        """
        raise NotImplementedError
        yield

    if sys.version_info >= (3, 3):
        def __await__(self):
            return self._wait().__await__()


class _AggregateWaitable(Waitable):
    """
    Base class for Waitables that take mutiple triggers in their constructor
    """
    __slots__ = ('triggers',)

    def __init__(self, *triggers):
        self.triggers = tuple(triggers)

        # Do some basic type-checking up front, rather than waiting until we
        # yield them.
        allowed_types = (Trigger, Waitable, decorators.RunningCoroutine)
        for trigger in self.triggers:
            if not isinstance(trigger, allowed_types):
                raise TypeError(
                    "All triggers must be instances of Trigger! Got: {}"
                    .format(type(trigger).__name__)
                )


@decorators.coroutine
def _wait_callback(trigger, callback):
    """
    Wait for a trigger, and call `callback` with the outcome of the yield.
    """
    try:
        ret = outcomes.Value((yield trigger))
    except BaseException as exc:
        # hide this from the traceback
        ret = outcomes.Error(exc).without_frames(['_wait_callback'])
    callback(ret)


class Combine(_AggregateWaitable):
    """
    Fires when all of *triggers* have fired.

    Like most triggers, this simply returns itself.
    """
    __slots__ = ()

    @decorators.coroutine
    def _wait(self):
        waiters = []
        e = Event()
        triggers = list(self.triggers)

        # start a parallel task for each trigger
        for t in triggers:
            # t=t is needed for the closure to bind correctly
            def on_done(ret, t=t):
                triggers.remove(t)
                if not triggers:
                    e.set()
                ret.get()  # re-raise any exception
            waiters.append(cocotb.fork(_wait_callback(t, on_done)))

        # wait for the last waiter to complete
        yield e.wait()
        raise ReturnValue(self)


class First(_AggregateWaitable):
    """
    Fires when the first trigger in *triggers* fires.

    Returns the result of the trigger that fired.

    As a shorthand, ``t = yield [a, b]`` can be used instead of
    ``t = yield First(a, b)``. Note that this shorthand is not available when
    using :keyword:`await`.

    .. note::
        The event loop is single threaded, so while events may be simultaneous
        in simulation time, they can never be simultaneous in real time.
        For this reason, the value of ``t_ret is t1`` in the following example
        is implementation-defined, and will vary by simulator::

            t1 = Timer(10, units='ps')
            t2 = Timer(10, units='ps')
            t_ret = yield First(t1, t2)
    """
    __slots__ = ()

    @decorators.coroutine
    def _wait(self):
        waiters = []
        e = Event()
        triggers = list(self.triggers)
        completed = []
        # start a parallel task for each trigger
        for t in triggers:
            def on_done(ret):
                completed.append(ret)
                e.set()
            waiters.append(cocotb.fork(_wait_callback(t, on_done)))

        # wait for a waiter to complete
        yield e.wait()

        # kill all the other waiters
        # TODO: Should this kill the coroutines behind any Join triggers?
        # Right now it does not.
        for w in waiters:
            w.kill()

        # These lines are the way they are to make tracebacks readable:
        #  - The comment helps the user understand why they are seeing the
        #    traceback, even if it is obvious top cocotb maintainers.
        #  - Raising ReturnValue on a separate line avoids confusion about what
        #    is actually raising the error, because seeing
        #    `raise Exception(foo())` in a traceback when in fact `foo()` itself
        #    raises is confusing. We can recombine once we drop python 2 support
        #  - Using `NullTrigger` here instead of `result = completed[0].get()`
        #    means we avoid inserting an `outcome.get` frame in the traceback
        first_trigger = NullTrigger(outcome=completed[0])
        result = yield first_trigger  # the first of multiple triggers that fired
        raise ReturnValue(result)


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

    @decorators.coroutine
    def _wait(self):
        trigger = self._type(self.signal)
        for _ in range(self.num_cycles):
            yield trigger
        raise ReturnValue(self)


@decorators.coroutine
def with_timeout(trigger, timeout_time, timeout_unit=None):
    """
    Waits on triggers, throws an exception if it waits longer than the given time.

    Usage:

    .. code-block:: python

        yield with_timeout(coro, 100, 'ns')
        yield with_timeout(First(coro, event.wait()), 100, 'ns')

    Args:
        trigger (cocotb_waitable):
            A single object that could be right of a :keyword:`yield`
            (or :keyword:`await` in Python 3) expression in cocotb.
        timeout_time (numbers.Real or decimal.Decimal):
            Time duration.
        timeout_unit (str or None, optional):
            Units of duration, accepts any values that :class:`~cocotb.triggers.Timer` does.

    Returns:
        First trigger that completed if timeout did not occur.

    Raises:
        :exc:`SimTimeoutError`: If timeout occurs.

    .. versionadded:: 1.3
    """
    timeout_timer = cocotb.triggers.Timer(timeout_time, timeout_unit)
    res = yield [timeout_timer, trigger]
    if res is timeout_timer:
        raise cocotb.result.SimTimeoutError
    else:
        raise ReturnValue(res)
