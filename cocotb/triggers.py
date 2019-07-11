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

if "COCOTB_SIM" in os.environ:
    import simulator
else:
    simulator = None

from cocotb.log import SimLog
from cocotb.result import raise_error, ReturnValue
from cocotb.utils import (
    get_sim_steps, get_time_from_sim_steps, with_metaclass,
    ParametrizedSingleton, exec_, lazy_property
)
from cocotb import decorators
from cocotb import outcomes
import cocotb


class TriggerException(Exception):
    pass

class Trigger(object):
    """Base class to derive from."""
    __slots__ = ('primed', '__weakref__')

    def __init__(self):
        self.primed = False

    @lazy_property
    def log(self):
        return SimLog("cocotb.%s" % (self.__class__.__name__), id(self))

    def prime(self, *args):
        """FIXME: document"""
        self.primed = True

    def unprime(self):
        """Remove any pending callbacks if necessary."""
        self.primed = False

    def __del__(self):
        """Ensure if a trigger drops out of scope we remove any pending
        callbacks."""
        self.unprime()

    def __str__(self):
        return self.__class__.__name__

    @property
    def _outcome(self):
        return outcomes.Value(self)

    # Once 2.7 is dropped, this can be run unconditionally
    if sys.version_info >= (3, 3):
        exec_(textwrap.dedent("""
        def __await__(self):
            # hand the trigger back to the scheduler trampoline
            return (yield self)
        """))


class PythonTrigger(Trigger):
    """Python triggers don't use GPI at all.
        For example notification of coroutine completion etc.

        TODO:
            Still need to implement unprime.
        """
    pass


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
        """Disable a primed trigger, can be reprimed"""
        if self.cbhdl != 0:
            simulator.deregister_callback(self.cbhdl)
        self.cbhdl = 0
        Trigger.unprime(self)

    def __del__(self):
        """Remove knowledge of the trigger"""
        if self.cbhdl != 0:
            self.unprime()
        Trigger.__del__(self)


class Timer(GPITrigger):
    """Execution will resume when the specified time period expires.

    Consumes simulation time.
    """
    def __init__(self, time_ps, units=None):
        GPITrigger.__init__(self)
        self.sim_steps = get_sim_steps(time_ps, units)

    def prime(self, callback):
        """Register for a timed callback"""
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_timed_callback(self.sim_steps,
                                                           callback, self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(%1.2fps)" % get_time_from_sim_steps(self.sim_steps,units='ps')


class ReadOnly(with_metaclass(ParametrizedSingleton, GPITrigger)):
    """Execution will resume when the readonly portion of the sim cycles is
    reached.
    """
    __slots__ = ()

    @classmethod
    def __singleton_key__(cls):
        return None

    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        """FIXME: document"""
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_readonly_callback(callback, self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(readonly)"


class ReadWrite(with_metaclass(ParametrizedSingleton, GPITrigger)):
    """Execution will resume when the readwrite portion of the sim cycles is
    reached.
    """
    __slots__ = ()

    @classmethod
    def __singleton_key__(cls):
        return None

    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        """FIXME: document"""
        if self.cbhdl == 0:
            # import pdb
            # pdb.set_trace()
            self.cbhdl = simulator.register_rwsynch_callback(callback, self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(readwritesync)"


class NextTimeStep(with_metaclass(ParametrizedSingleton, GPITrigger)):
    """Execution will resume when the next time step is started."""
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
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(nexttimestep)"


class _EdgeBase(with_metaclass(ParametrizedSingleton, GPITrigger)):
    """Execution will resume when an edge occurs on the provided signal."""
    __slots__ = ('signal',)

    @classmethod
    @property
    def _edge_type(self):
        """The edge type, as understood by the C code. Must be set in subclasses."""
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
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        super(_EdgeBase, self).prime()

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal._name


class RisingEdge(_EdgeBase):
    """Triggers on the rising edge of the provided signal."""
    __slots__ = ()
    _edge_type = 1


class FallingEdge(_EdgeBase):
    """Triggers on the falling edge of the provided signal."""
    __slots__ = ()
    _edge_type = 2


class Edge(_EdgeBase):
    """Triggers on either edge of the provided signal."""
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
        Trigger.prime(self)

    def __call__(self):
        self._callback(self)


class Event(object):
    """Event to permit synchronisation between two coroutines."""

    def __init__(self, name=""):
        self._pending = []
        self.name = name
        self.fired = False
        self.data = None

    def _prime_trigger(self, trigger, callback):
        self._pending.append(trigger)

    def set(self, data=None):
        """Wake up any coroutines blocked on this event."""
        self.fired = True
        self.data = data

        p = self._pending[:]

        self._pending = []

        for trigger in p:
            trigger()

    def wait(self):
        """This can be yielded to block this coroutine
        until another wakes it.

        If the event has already been fired, this returns ``NullTrigger``.
        To reset the event (and enable the use of ``wait`` again),
        :meth:`~cocotb.triggers.Event.clear` should be called.
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
        Trigger.prime(self)

    def __call__(self):
        self._callback(self)


class Lock(object):
    """Lock primitive (not re-entrant)."""

    def __init__(self, name=""):
        self._pending_unprimed = []
        self._pending_primed = []
        self.name = name
        self.locked = False

    def _prime_trigger(self, trigger, callback):
        self._pending_unprimed.remove(trigger)

        if not self.locked:
            self.locked = True
            callback(trigger)
        else:
            self._pending_primed.append(trigger)

    def acquire(self):
        """This can be yielded to block until the lock is acquired."""
        trig = _Lock(self)
        self._pending_unprimed.append(trig)
        return trig

    def release(self):
        """Release the lock."""
        if not self.locked:
            raise_error(self, "Attempt to release an unacquired Lock %s" %
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
    """
    A trigger that fires instantly, primarily for internal scheduler use.
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


class Join(with_metaclass(ParametrizedSingleton, PythonTrigger)):
    """Join a coroutine, firing when it exits."""
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
        """FIXME: document"""
        return self._coroutine.retval

    def prime(self, callback):
        """FIXME: document"""
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
    supporting python versions (>=3.3).
    """
    __slots__ = ()
    @decorators.coroutine
    def _wait(self):
        """
        Should be implemented by the subclass. Called by `yield self` to
        convert the waitable object into a coroutine.

        ReturnValue can be used here
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

    def __init__(self, *args):
        self.triggers = tuple(args)

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
    Wait for a trigger, and call `callback` with the outcome of the yield
    """
    try:
        ret = outcomes.Value((yield trigger))
    except BaseException as exc:
        ret = outcomes.Error(exc)
    callback(ret)


class Combine(_AggregateWaitable):
    """
    Waits until all the passed triggers have fired.

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
    Wait for the first of multiple triggers.

    Returns the result of the trigger that fired.

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

        # get the result from the first task
        ret = completed[0]
        raise ReturnValue(ret.get())


class ClockCycles(Waitable):
    """
    Execution will resume after *num_cycles* rising edges or *num_cycles* falling edges.
    """
    def __init__(self, signal, num_cycles, rising=True):
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
