#!/usr/bin/env python

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
    Coroutine scheduler.


FIXME: We have a problem here.  If a coroutine schedules a read-only but we
also have pending writes we have to schedule the ReadWrite callback before
the ReadOnly (and this is invalid, at least in Modelsim).
"""
import collections
import os
import logging


# For autodocumentation don't need the extension modules
if "SPHINX_BUILD" in os.environ:
    simulator = None
else:
    import simulator

# Debug mode controlled by environment variables
if "COCOTB_ENABLE_PROFILING" in os.environ:
    import cProfile, StringIO, pstats
    _profile = cProfile.Profile()
    _profiling = True
else:
    _profiling = False

# Sadly the python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
if "COCOTB_SCHEDULER_DEBUG" in os.environ:
    _debug = True
else:
    _debug = False


import cocotb
import cocotb.decorators
from cocotb.triggers import (Trigger, GPITrigger, Timer, ReadOnly,
                             _NextTimeStep, _ReadWrite)
from cocotb.log import SimLog
from cocotb.result import (TestComplete, TestError, ReturnValue, raise_error,
                           create_error)


class Scheduler(object):
    """
    The main scheduler.

    Here we accept callbacks from the simulator and schedule the appropriate
    coroutines.

    A callback fires, causing the `react`_ method to be called, with the
    trigger that caused the callback as the first argument.

    We look up a list of coroutines to schedule (indexed by the trigger) and
    schedule them in turn. NB implementors should not depend on the scheduling
    order!

    Some additional management is required since coroutines can return a list
    of triggers, to be scheduled when any one of the triggers fires.  To
    ensure we don't receive spurious callbacks, we have to un-prime all the
    other triggers when any one fires.

    Due to the simulator nuances and fun with delta delays we have the
    following modes:

    Normal mode
        - Callbacks cause coroutines to be scheduled
        - Any pending writes are cached and do not happen immediately

    ReadOnly mode
        - Corresponds to cbReadOnlySynch (VPI) or vhpiCbLastKnownDeltaCycle
          (VHPI).  In this state we are not allowed to perform writes.

    Write mode
        - Corresponds to cbReadWriteSynch (VPI) or vhpiCbEndOfProcesses (VHPI)
          In this mode we play back all the cached write updates.

    We can legally transition from normal->write by registering a ReadWrite
    callback, however usually once a simulator has entered the ReadOnly phase
    of a given timestep then we must move to a new timestep before performing
    any writes.  The mechanism for moving to a new timestep may not be
    consistent across simulators and therefore we provide an abstraction to
    assist with compatibility.


    Unless a coroutine has explicitly requested to be scheduled in ReadOnly
    mode (for example wanting to sample the finally settled value after all
    delta delays) then it can reasonably be expected to be scheduled during
    "normal mode" i.e. where writes are permitted.
    """

    _MODE_NORMAL   = 1  # noqa
    _MODE_READONLY = 2  # noqa
    _MODE_WRITE    = 3  # noqa
    _MODE_TERM     = 4  # noqa

    # Singleton events, recycled to avoid spurious object creation
    _readonly = ReadOnly()
    _next_timestep = _NextTimeStep()
    _readwrite = _ReadWrite()
    _timer1 = Timer(1)
    _timer0 = Timer(0)

    def __init__(self):

        self.log = SimLog("cocotb.scheduler")
        if _debug:
            self.log.setLevel(logging.DEBUG)

        # A dictionary of pending coroutines for each trigger,
        # indexed by trigger
        self._trigger2coros = collections.defaultdict(list)

        # A dictionary of pending triggers for each coroutine, indexed by coro
        self._coro2triggers = collections.defaultdict(list)

        # Our main state
        self._mode = Scheduler._MODE_NORMAL

        # A dictionary of pending writes
        self._writes = {}

        self._pending_coros = []
        self._pending_callbacks = []
        self._pending_triggers = []

        self._terminate = False
        self._test_result = None
        self._entrypoint = None

        # Select the appropriate scheduling algorithm for this simulator
        self.advance = self.default_scheduling_algorithm

    def default_scheduling_algorithm(self):
        """
        Decide whether we need to schedule our own triggers (if at all) in
        order to progress to the next mode.

        This algorithm has been tested against the following simulators:
            Icarus Verilog
        """
        if not self._terminate and self._writes:

            if self._mode == Scheduler._MODE_NORMAL:
                if not self._readwrite.primed:
                    self._readwrite.prime(self.react)
            elif not self._next_timestep.primed:
                self._next_timestep.prime(self.react)

        elif self._terminate:
            if _debug:
                self.log.debug("Test terminating, scheduling Timer")

            for t in self._trigger2coros:
                t.unprime()

            for t in [self._readwrite, self._readonly, self._next_timestep,
                      self._timer1, self._timer0]:
                if t.primed:
                    t.unprime()

            self._timer1.prime(self.begin_test)
            self._trigger2coros = collections.defaultdict(list)
            self._coro2triggers = collections.defaultdict(list)
            self._terminate = False
            self._mode = Scheduler._MODE_TERM

    def begin_test(self, trigger=None):
        """
        Called to initiate a test.

        Could be called on start-up or from a callback
        """
        if _debug:
            self.log.debug("begin_test called with trigger: %s" %
                           (str(trigger)))
        if _profiling:
            ps = pstats.Stats(_profile).sort_stats('cumulative')
            ps.dump_stats("test_profile.pstat")
            _profile.enable()

        self._mode = Scheduler._MODE_NORMAL
        if trigger is not None:
            trigger.unprime()

        # Issue previous test result, if there is one
        if self._test_result is not None:
            if _debug:
                self.log.debug("Issue test result to regresssion object")
            cocotb.regression.handle_result(self._test_result)
            self._test_result = None
        if self._entrypoint is not None:
            test = self._entrypoint
            self._entrypoint = None
            self.schedule(test)
            self.advance()

        if _profiling:
            _profile.disable()

    def react(self, trigger, depth=0):
        """
        React called when a trigger fires.

        We find any coroutines that are waiting on the particular trigger and
        schedule them.
        """
        if _profiling and not depth:
            _profile.enable()

        # When a trigger fires it is unprimed internally
        if _debug:
            self.log.debug("Trigger fired: %s" % str(trigger))
        # trigger.unprime()

        if self._mode == Scheduler._MODE_TERM:
            if _debug:
                self.log.debug("Ignoring trigger %s since we're terminating" %
                               str(trigger))
            return

        if trigger is self._readonly:
            self._mode = Scheduler._MODE_READONLY
        # Only GPI triggers affect the simulator scheduling mode
        elif isinstance(trigger, GPITrigger):
            self._mode = Scheduler._MODE_NORMAL

        # We're the only source of ReadWrite triggers which are only used for
        # playing back any cached signal updates
        if trigger is self._readwrite:

            if _debug:
                self.log.debug("Writing cached signal updates")

            while self._writes:
                handle, value = self._writes.popitem()
                handle.setimmediatevalue(value)

            self._readwrite.unprime()

            if _profiling:
                _profile.disable()
            return

        # Similarly if we've scheduled our next_timestep on way to readwrite
        if trigger is self._next_timestep:

            if not self._writes:
                self.log.error(
                    "Moved to next timestep without any pending writes!")
            else:
                self.log.debug(
                    "Priming ReadWrite trigger so we can playback writes")
                self._readwrite.prime(self.react)

            if _profiling:
                _profile.disable()
            return

        if trigger not in self._trigger2coros:

            # GPI triggers should only be ever pending if there is an
            # associated coroutine waiting on that trigger, otherwise it would
            # have been unprimed already
            if isinstance(trigger, GPITrigger):
                self.log.critical(
                    "No coroutines waiting on trigger that fired: %s" %
                    str(trigger))

                trigger.log.info("I'm the culprit")
            # For Python triggers this isn't actually an error - we might do
            # event.set() without knowing whether any coroutines are actually
            # waiting on this event, for example
            elif _debug:
                self.log.debug(
                    "No coroutines waiting on trigger that fired: %s" %
                    str(trigger))

            if _profiling:
                _profile.disable()
            return

        # Scheduled coroutines may append to our waiting list so the first
        # thing to do is pop all entries waiting on this trigger.
        scheduling = self._trigger2coros.pop(trigger)

        if _debug:
            debugstr = "\n\t".join([coro.__name__ for coro in scheduling])
            if len(scheduling):
                debugstr = "\n\t" + debugstr
            self.log.debug("%d pending coroutines for event %s%s" %
                           (len(scheduling), str(trigger), debugstr))

        # If the coroutine was waiting on multiple triggers we may be able
        # to unprime the other triggers that didn't fire
        for coro in scheduling:
            for pending in self._coro2triggers[coro]:
                for others in self._trigger2coros[pending]:
                    if others not in scheduling:
                        break
                else:
                    # if pending is not trigger and pending.primed:
                    #     pending.unprime()
                    if pending.primed:
                        pending.unprime()
                    del self._trigger2coros[pending]

        for coro in scheduling:
            self.schedule(coro, trigger=trigger)
            if _debug:
                self.log.debug("Scheduled coroutine %s" % (coro.__name__))

        while self._pending_triggers:
            if _debug:
                self.log.debug("Scheduling pending trigger %s" %
                               (str(self._pending_triggers[0])))
            self.react(self._pending_triggers.pop(0), depth=depth + 1)

        # We only advance for GPI triggers
        if not depth and isinstance(trigger, GPITrigger):
            self.advance()

            if _debug:
                self.log.debug("All coroutines scheduled, handing control back"
                               " to simulator")

            if _profiling:
                _profile.disable()
        return

    def unschedule(self, coro):
        """Unschedule a coroutine.  Unprime any pending triggers"""

        for trigger in self._coro2triggers[coro]:
            if coro in self._trigger2coros[trigger]:
                self._trigger2coros[trigger].remove(coro)
            if not self._trigger2coros[trigger]:
                trigger.unprime()
                del self._trigger2coros[trigger]
        del self._coro2triggers[coro]

        if coro._join in self._trigger2coros:
            self._pending_triggers.append(coro._join)

        # Remove references to allow GC to clean up
        del coro._join

    def save_write(self, handle, value):
        if self._mode == Scheduler._MODE_READONLY:
            raise Exception("Write to object {0} was scheduled during a read-only sync phase.".format(handle._name))
        self._writes[handle] = value

    def _coroutine_yielded(self, coro, triggers):
        """
        Prime the triggers and update our internal mappings
        """
        self._coro2triggers[coro] = triggers

        for trigger in triggers:

            self._trigger2coros[trigger].append(coro)
            if not trigger.primed:
                try:
                    trigger.prime(self.react)
                except Exception as e:
                    # Convert any exceptions into a test result
                    self.finish_test(
                        create_error(self, "Unable to prime trigger %s: %s" %
                                     (str(trigger), str(e))))

    def queue(self, coroutine):
        """Queue a coroutine for execution"""
        self._pending_coros.append(coroutine)

    def add(self, coroutine):
        """
        Add a new coroutine.

        Just a wrapper around self.schedule which provides some debug and
        useful error mesages in the event of common gotchas
        """
        if isinstance(coroutine, cocotb.decorators.coroutine):
            self.log.critical(
                "Attempt to schedule a coroutine that hasn't started")
            coroutine.log.error("This is the failing coroutine")
            self.log.warning(
                "Did you forget to add parentheses to the @test decorator?")
            self._test_result = TestError(
                "Attempt to schedule a coroutine that hasn't started")
            self._terminate = True
            return

        elif not isinstance(coroutine, cocotb.decorators.RunningCoroutine):
            self.log.critical(
                "Attempt to add something to the scheduler which isn't a "
                "coroutine")
            self.log.warning(
                "Got: %s (%s)" % (str(type(coroutine)), repr(coroutine)))
            self.log.warning("Did you use the @coroutine decorator?")
            self._test_result = TestError(
                "Attempt to schedule a coroutine that hasn't started")
            self._terminate = True
            return

        if _debug:
            self.log.debug("Adding new coroutine %s" % coroutine.__name__)

        self.schedule(coroutine)
        self.advance()
        return coroutine

    def new_test(self, coroutine):
        self._entrypoint = coroutine

    def schedule(self, coroutine, trigger=None):
        """
        Schedule a coroutine by calling the send method

        Args:
            coroutine (cocotb.decorators.coroutine): The coroutine to schedule

            trigger (cocotb.triggers.Trigger): The trigger that caused this
                                                coroutine to be scheduled
        """
        if hasattr(trigger, "pass_retval"):
            sendval = trigger.retval
            if _debug:
                coroutine.log.debug("Scheduling with ReturnValue(%s)" %
                                    (repr(sendval)))
        else:
            sendval = trigger
            if _debug:
                coroutine.log.debug("Scheduling with %s" % str(trigger))

        try:
            result = coroutine.send(sendval)
            if _debug:
                self.log.debug("Coroutine %s yielded %s (mode %d)" %
                               (coroutine.__name__, str(result), self._mode))

        # TestComplete indication is game over, tidy up
        except TestComplete as test_result:
            # Tag that close down is needed, save the test_result
            # for later use in cleanup handler
            self.log.debug("TestComplete received: %s" % test_result.__class__.__name__)
            self.finish_test(test_result)
            return

        # Normal co-routine completion
        except cocotb.decorators.CoroutineComplete as exc:
            if _debug:
                self.log.debug("Coroutine completed: %s" % str(coroutine))
            self.unschedule(coroutine)
            return

        # Don't handle the result if we're shutting down
        if self._terminate:
            return

        # Queue current routine to schedule when the nested routine exits
        if isinstance(result, cocotb.decorators.RunningCoroutine):
            if _debug:
                self.log.debug("Scheduling nested co-routine: %s" %
                               result.__name__)

            self.queue(result)
            new_trigger = result.join()
            self._coroutine_yielded(coroutine, [new_trigger])

        elif isinstance(result, Trigger):
            self._coroutine_yielded(coroutine, [result])

        elif (isinstance(result, list) and
                not [t for t in result if not isinstance(t, Trigger)]):
            self._coroutine_yielded(coroutine, result)

        else:
            msg = ("Coroutine %s yielded something the scheduler can't handle"
                   % str(coroutine))
            msg += ("\nGot type: %s repr: %s str: %s" %
                    (type(result), repr(result), str(result)))
            msg += "\nDid you forget to decorate with @cocotb.coroutine?"
            try:
                raise_error(self, msg)
            except Exception as e:
                self.finish_test(e)

        # Handle any newly queued coroutines that need to be scheduled
        while self._pending_coros:
            self.add(self._pending_coros.pop(0))

        while self._pending_callbacks:
            self._pending_callbacks.pop(0)()

    def finish_test(self, test_result):
        """Cache the test result and set the terminate flag"""
        self.log.debug("finish_test called with %s" % (repr(test_result)))
        if not self._terminate:
            self._terminate = True
            self._test_result = test_result
            self.cleanup()

    def finish_scheduler(self, test_result):
        """Directly call into the regression manager and end test
           once we return the sim will close us so no cleanup is needed"""
        self.log.debug("Issue sim closedown result to regresssion object")
        cocotb.regression.handle_result(test_result)

    def cleanup(self):
        """
        Clear up all our state

        Unprime all pending triggers and kill off any coroutines
        """
        for trigger, waiting in dict(self._trigger2coros).items():
            for coro in waiting:
                if _debug:
                    self.log.debug("Killing %s" % str(coro))
                coro.kill()
