''' Copyright (c) 2013 Potential Ventures Ltd
Copyright (c) 2013 SolarFlare Communications Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd,
      SolarFlare Communications Inc nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. '''

"""
    A collections of triggers which a testbench can 'yield'
"""
import os

# Only for in case of simulation, disable for  autodocumentation
if "COCOTB_SIM" in os.environ:
    import simulator
else:
    simulator = None

from cocotb.log import SimLog
from cocotb.result import raise_error
from cocotb.utils import get_sim_steps, get_time_from_sim_steps


class TriggerException(Exception):
    pass


class Trigger(object):
    """Base class to derive from"""
    def __init__(self):
        self.log = SimLog("cocotb.%s" % (self.__class__.__name__), id(self))
        self.signal = None
        self.primed = False

    def prime(self, *args):
        self.primed = True

    def unprime(self):
        """Remove any pending callbacks if necessary"""
        self.primed = False

    def __del__(self):
        """Ensure if a trigger drops out of scope we remove any pending
        callbacks"""
        self.unprime()

    def __str__(self):
        return self.__class__.__name__


class PythonTrigger(Trigger):
    """Python triggers don't use GPI at all

        For example notification of coroutine completion etc

        TODO:
            Still need to implement unprime
        """
    pass


class GPITrigger(Trigger):
    """
    Base Trigger class for GPI triggers

    Consumes simulation time
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
    """
    Execution will resume when the specified time period expires

    Consumes simulation time
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

class _ReadOnly(GPITrigger):
    """
    Execution will resume when the readonly portion of the sim cycles is
    readched
    """
    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_readonly_callback(callback, self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(readonly)"

_ro = _ReadOnly()


def ReadOnly():
    return _ro


class _ReadWrite(GPITrigger):
    """
    Execution will resume when the readwrite porttion of the sim cycles is
    reached
    """
    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        if self.cbhdl == 0:
            # import pdb
            # pdb.set_trace()
            self.cbhdl = simulator.register_rwsynch_callback(callback, self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(readwritesync)"

_rw = _ReadWrite()


def ReadWrite():
    return _rw


class _NextTimeStep(GPITrigger):
    """
    Execution will resume when the next time step is started
    """
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

_nxts = _NextTimeStep()


def NextTimeStep():
    return _nxts


class _Edge(GPITrigger):
    """
    Execution will resume when an edge occurs on the provided signal
    """
    def __init__(self, signal):
        GPITrigger.__init__(self)
        self.signal = signal

    def prime(self, callback):
        """Register notification of a value change via a callback"""
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_value_change_callback(self.signal.
                                                                  _handle,
                                                                  callback,
                                                                  3,
                                                                  self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal._name

def Edge(signal):
    return signal._e_edge


class _RisingOrFallingEdge(_Edge):
    def __init__(self, signal, rising):
        _Edge.__init__(self, signal)
        if rising is True:
            self._rising = 1
        else:
            self._rising = 2

    def prime(self, callback):
        if self.cbhdl == 0:
            self.cbhdl = simulator.register_value_change_callback(self.signal.
                                                                  _handle,
                                                                  callback,
                                                                  self._rising,
                                                                  self)
            if self.cbhdl == 0:
                raise_error(self, "Unable set up %s Trigger" % (str(self)))
        Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal._name


class _RisingEdge(_RisingOrFallingEdge):
    """
    Execution will resume when a rising edge occurs on the provided signal
    """
    def __init__(self, signal):
        _RisingOrFallingEdge.__init__(self, signal, rising=True)


def RisingEdge(signal):
    return signal._r_edge


class _FallingEdge(_RisingOrFallingEdge):
    """
    Execution will resume when a falling edge occurs on the provided signal
    """
    def __init__(self, signal):
        _RisingOrFallingEdge.__init__(self, signal, rising=False)


def FallingEdge(signal):
    return signal._f_edge


class ClockCycles(_Edge):
    """
    Execution will resume after N rising edges or N falling edges
    """
    def __init__(self, signal, num_cycles, rising=True):
        _Edge.__init__(self, signal)
        self.num_cycles = num_cycles
        if rising is True:
            self._rising = 1
        else:
            self._rising = 2

    def prime(self, callback):
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
    """
    Combines multiple triggers together.  Coroutine will continue when all
    triggers have fired
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
        for trigger in self._triggers:
            trigger.unprime()


class _Event(PythonTrigger):
    """
    Unique instance used by the Event object.

    One created for each attempt to wait on the event so that the scheduler
    can maintain a dictionary of indexing each individual coroutine

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
    """
    Event to permit synchronisation between two coroutines
    """
    def __init__(self, name=""):
        PythonTrigger.__init__(self)
        self._pending = []
        self.name = name
        self.fired = False
        self.data = None

    def prime(self, callback, trigger):
        self._pending.append(trigger)
        Trigger.prime(self)

    def set(self, data=None):
        """Wake up any coroutines blocked on this event"""
        self.fired = True
        self.data = data

        p = self._pending[:]

        self._pending = []

        for trigger in p:
            trigger()

    def wait(self):
        """This can be yielded to block this coroutine
        until another wakes it"""
        return _Event(self)

    def clear(self):
        """Clear this event that's fired.

        Subsequent calls to wait will block until set() is called again"""
        self.fired = False

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.name


class _Lock(PythonTrigger):
    """
    Unique instance used by the Lock object.

    One created for each attempt to acquire the Lock so that the scheduler
    can maintain a dictionary of indexing each individual coroutine

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


class Lock(PythonTrigger):
    """
    Lock primitive (not re-entrant)
    """

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
        """This can be yielded to block until the lock is acquired"""
        trig = _Lock(self)
        self._pending_unprimed.append(trig)
        return trig

    def release(self):

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
    Trigger for internal interfacing use call the callback as soon
    as it is primed and then remove it's self from the scheduler
    """
    def __init__(self, name=""):
        Trigger.__init__(self)
        self._callback = None
        self.name = name

    def prime(self, callback):
        callback(self)


class _Join(PythonTrigger):
    """
    Join a coroutine, firing when it exits
    """
    def __init__(self, coroutine):
        PythonTrigger.__init__(self)
        self._coroutine = coroutine
        self.pass_retval = True

    @property
    def retval(self):
        return self._coroutine.retval

    # def prime(self, callback):
        # """Register our calback for when the coroutine exits"""
        # Trigger.prime(self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self._coroutine.__name__


def Join(coro):
    return coro._join
