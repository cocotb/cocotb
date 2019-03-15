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
import weakref

if "COCOTB_SIM" in os.environ:
    import simulator
else:
    simulator = None

from cocotb.log import SimLog
from cocotb.result import raise_error
from cocotb.utils import (
    get_sim_steps, get_time_from_sim_steps, with_metaclass,
    ParametrizedSingleton
)
from cocotb import outcomes

class TriggerException(Exception):
    pass

class Trigger(object):
    """Base class to derive from."""
    
    def __init__(self):
        self.log = SimLog("cocotb.%s" % (self.__class__.__name__), id(self))
        self.signal = None
        self.primed = False

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
    
    _edge_type = 1


class FallingEdge(_EdgeBase):
    """Triggers on the falling edge of the provided signal."""
    
    _edge_type = 2


class Edge(_EdgeBase):
    """Triggers on either edge of the provided signal."""
    _edge_type = 3


class ClockCycles(GPITrigger):
    """Execution will resume after *num_cycles* rising edges or *num_cycles* falling edges."""
    
    def __init__(self, signal, num_cycles, rising=True):
        super(ClockCycles, self).__init__()
        self.signal = signal
        self.num_cycles = num_cycles
        if rising is True:
            self._rising = 1
        else:
            self._rising = 2

    def prime(self, callback):
        """FIXME: document"""
        self._callback = callback

        def _check(obj):
            self.unprime()

            if self.signal.value:
                self.num_cycles -= 1

                if self.num_cycles <= 0:
                    self._callback(self)
                    return

            self.cbhdl = simulator.register_value_change_callback(self.signal.
                                                                  _handle,
                                                                  _check,
                                                                  self._rising,
                                                                  self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))

        self.cbhdl = simulator.register_value_change_callback(self.signal.
                                                              _handle,
                                                              _check,
                                                              self._rising,
                                                              self)
        if self.cbhdl == 0:
            raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal._name


class Combine(PythonTrigger):
    """Combines multiple triggers together.  Coroutine will continue when all
    triggers have fired.
    """

    def __init__(self, *args):
        PythonTrigger.__init__(self)
        self._triggers = args
        # TODO: check that trigger is an iterable containing
        # only Trigger objects
        try:
            for trigger in self._triggers:
                if not isinstance(trigger, Trigger):
                    raise TriggerException("All combined triggers must be "
                                           "instances of Trigger! Got: %s" %
                                           trigger.__class__.__name__)
        except Exception:
            raise TriggerException("%s requires a list of Trigger objects" %
                                   self.__class__.__name__)

    def prime(self, callback):
        self._callback = callback
        self._fired = []
        for trigger in self._triggers:
            trigger.prime(self._check_all_fired)
        Trigger.prime(self)

    def _check_all_fired(self, trigger):
        self._fired.append(trigger)
        if self._fired == self._triggers:
            self._callback(self)

    def unprime(self):
        """FIXME: document"""
        for trigger in self._triggers:
            trigger.unprime()


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
        self.parent.prime(callback, self)
        Trigger.prime(self)

    def __call__(self):
        self._callback(self)


class Event(PythonTrigger):
    """Event to permit synchronisation between two coroutines."""
    
    def __init__(self, name=""):
        PythonTrigger.__init__(self)
        self._pending = []
        self.name = name
        self.fired = False
        self.data = None

    def prime(self, callback, trigger):
        """FIXME: document"""
        self._pending.append(trigger)
        Trigger.prime(self)

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
            return NullTrigger()
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
        self.parent.prime(callback, self)
        Trigger.prime(self)

    def __call__(self):
        self._callback(self)


class Lock(PythonTrigger):
    """Lock primitive (not re-entrant)."""

    def __init__(self, name=""):
        PythonTrigger.__init__(self)
        self._pending_unprimed = []
        self._pending_primed = []
        self.name = name
        self.locked = False

    def prime(self, callback, trigger):
        Trigger.prime(self)

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
    """Trigger for internal interfacing use call the callback as soon
    as it is primed and then remove itself from the scheduler.
    """
    def __init__(self, name=""):
        Trigger.__init__(self)
        self._callback = None
        self.name = name

    def prime(self, callback):
        callback(self)


class Join(with_metaclass(ParametrizedSingleton, PythonTrigger)):
    """Join a coroutine, firing when it exits."""
    
    @classmethod
    def __singleton_key__(cls, coroutine):
        return coroutine

    def __init__(self, coroutine):
        super(Join, self).__init__()
        self._coroutine = coroutine
        self.pass_retval = True

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
