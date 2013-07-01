''' Copyright (c) 2013 Potential Ventures Ltd
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Potential Ventures Ltd nor the
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
import logging
import simulator



class TriggerException(Exception):
    pass

class Trigger(object):
    """Base class to derive from"""
    def __init__(self):
        self.log = logging.getLogger("cocotb.%s.0x%x" % (self.__class__.__name__, id(self)))
        self.peers = []
        self.signal = None

    def unprime(self):
        """Remove any pending callbacks if necessary"""
	if self.peers:
           self.peers = None
            
    def addpeers(self, peers):
        """Store any relate triggers"""
        for elem in peers:
           if elem is not self:
               self.peers.append(elem)

    def clearpeers(self):
        """Call _clearpeers on each trigger that is not me"""
        return self.peers

    def __del__(self):
        """Ensure if a trigger drops out of scope we remove any pending callbacks"""
        self.unprime()

class GPITrigger(Trigger):
    """
    Execution will resume when the specified time period expires

    Consumes simulation time
    """
    def __init__(self):
        Trigger.__init__(self)
        self.cbhdl = None

    def unprime(self):
        """Unregister a prior registered timed callback"""
        Trigger.unprime(self)
        if self.cbhdl is not None:
            simulator.deregister_callback(self.cbhdl)
            self.cbhdl = None


class Timer(GPITrigger):
    """
    Execution will resume when the specified time period expires

    Consumes simulation time
    """
    def __init__(self, time_ps):
        GPITrigger.__init__(self)
        self.time_ps = time_ps

    def prime(self, callback):
        """Register for a timed callback"""
        self.cbhdl = simulator.register_timed_callback(self.time_ps, callback, self)

    def __str__(self):
        return self.__class__.__name__ + "(%dps)" % self.time_ps

class Edge(GPITrigger):
    """
    Execution will resume when an edge occurs on the provided signal
    """
    def __init__(self, signal):
        GPITrigger.__init__(self)
        self.signal = signal

    def prime(self, callback):
        """Register notification of a value change via a callback"""
        self.cbhdl = simulator.register_value_change_callback(self.signal._handle, callback, self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal.name

class ReadOnly(GPITrigger):
    """
    Execution will resume when the readonly portion of the sim cycles is
    readched
    """
    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        self.cbhdl = simulator.register_readonly_callback(callback, self)

    def __str__(self):
        return self.__class__.__name__ + "(readonly)"

class ReadWrite(GPITrigger):
    """
    Execution will resume when the readwrite porttion of the sim cycles is
    reached
    """
    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        self.cbhdl = simulator.register_rwsynch_callback(callback, self)

    def __str__(self):
        return self.__class__.__name__ + "(readwritesync)"

class NextTimeStep(GPITrigger):
    """
    Execution will resume when the next time step is started
    """
    def __init__(self):
        GPITrigger.__init__(self)

    def prime(self, callback):
        self.cbhdl = simulator.register_nextstep_callback(callback, self)

    def __str__(self):
        return self.__class__.__name__ + "(nexttimestep)"

class RisingEdge(Edge):
    """
    Execution will resume when a rising edge occurs on the provided signal
    """
    def __init__(self, signal):
        Edge.__init__(self, signal)

    def prime(self, callback):
        self._callback = callback

        def _check(obj):
            if self.signal.value:
                self._callback(self)
            else:
                self.cbhdl = simulator.register_value_change_callback(self.signal._handle, _check, self)

        self.cbhdl = simulator.register_value_change_callback(self.signal._handle, _check, self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal.name

class ClockCycles(Edge):
    """
    Execution will resume after N rising edges
    """
    def __init__(self, signal, num_cycles):
        Edge.__init__(self, signal)
        self.num_cycles = num_cycles

    def prime(self, callback):
        self._callback = callback

        def _check(obj):
            if self.signal.value:
                self.num_cycles -= 1

                if self.num_cycles <= 0:
                    self._callback(self)
                    return

            self.cbhdl = simulator.register_value_change_callback(self.signal._handle, _check, self)

        self.cbhdl = simulator.register_value_change_callback(self.signal._handle, _check, self)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.signal.name


class Combine(Trigger):
    """
    Combines multiple triggers together.  Coroutine will continue when all
    triggers have fired
    """

    def __init__(self, *args):
        Trigger.__init__(self)
        self._triggers = args
        # TODO: check that trigger is an iterable containing only Trigger objects
        try:
            for trigger in self._triggers:
                if not isinstance(trigger, Trigger):
                    raise TriggerException("All combined triggers must be instances of Trigger! Got: %s" % trigger.__class__.__name__)
        except Exception:
            raise TriggerException("%s requires a list of Trigger objects" % self.__class__.__name__)

    def prime(self, callback):
        self._callback = callback
        self._fired = []
        for trigger in self._triggers:
            trigger.prime(self._check_all_fired)

    def _check_all_fired(self, trigger):
        self._fired.append(trigger)
        if self._fired == self._triggers:
            self._callback(self)

    def unprime(self):
        for trigger in self._triggers:
            trigger.unprime()


class Event(Trigger):
    """
    Event to permit synchronisation between two coroutines
    """
    def __init__(self, name=""):
        Trigger.__init__(self)
        self._callback = None
        self.name = name

    def prime(self, callback):
        self._callback = callback

    def set(self):
        """Wake up any coroutines blocked on this event"""
        if not self._callback:
            pass # nobody waiting
        self._callback(self)

    def wait(self):
        """This can be yielded to block this coroutine until another wakes it"""
        return self

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self.name

class Join(Trigger):
    """
    Join a coroutine, firing when it exits
    """
    def __init__(self, coroutine):
        Trigger.__init__(self)
        self._coroutine = coroutine

    def prime(self, callback):
        """Register our calback for when the coroutine exits"""
        def _cb():
            callback(self)

        self._coroutine._callbacks.append(_cb)
        self.log.debug("Primed on %s" % self._coroutine.__name__)

    def __str__(self):
        return self.__class__.__name__ + "(%s)" % self._coroutine.__name__
