#!/usr/bin/env python

# Copyright (c) 2013, 2018 Potential Ventures Ltd
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

"""Coroutine scheduler.


FIXME: We have a problem here.  If a coroutine schedules a read-only but we
also have pending writes we have to schedule the ReadWrite callback before
the ReadOnly (and this is invalid, at least in Modelsim).
"""
import collections
import copy
import os
import time
import logging
import threading

if "COCOTB_SIM" in os.environ:
    import simulator
else:
    simulator = None

# Debug mode controlled by environment variables
if "COCOTB_ENABLE_PROFILING" in os.environ:
    import cProfile, StringIO, pstats
    _profile = cProfile.Profile()
    _profiling = True
else:
    _profiling = False

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
if "COCOTB_SCHEDULER_DEBUG" in os.environ:
    _debug = True
else:
    _debug = False


import cocotb
import cocotb.decorators
from cocotb.triggers import (Trigger, GPITrigger, Timer, ReadOnly, PythonTrigger,
                             NextTimeStep, ReadWrite, Event, Join)
from cocotb.log import SimLog
from cocotb.result import (TestComplete, TestError, ReturnValue, raise_error,
                           create_error, ExternalException)
from cocotb.utils import nullcontext


class profiling_context(object):
    """ Context manager that profiles its contents """
    def __enter__(self):
        _profile.enable()

    def __exit__(self, *excinfo):
        _profile.disable()


from cocotb import outcomes

class external_state(object):
    INIT = 0
    RUNNING = 1
    PAUSED = 2
    EXITED = 3

@cocotb.decorators.public
class external_waiter(object):

    def __init__(self):
        self._outcome = None
        self.thread = None
        self.event = Event()
        self.state = external_state.INIT
        self.cond = threading.Condition()
        self._log = SimLog("cocotb.external.thead.%s" % self.thread, id(self))

    @property
    def result(self):
        return self._outcome.get()

    def _propogate_state(self, new_state):
        with self.cond:
            if _debug:
                self._log.debug("Changing state from %d -> %d from %s" % (self.state, new_state, threading.current_thread()))
            self.state = new_state
            self.cond.notify()

    def thread_done(self):
        if _debug:
            self._log.debug("Thread finished from %s" % (threading.current_thread()))
        self._propogate_state(external_state.EXITED)

    def thread_suspend(self):
        self._propogate_state(external_state.PAUSED)

    def thread_start(self):
        if self.state > external_state.INIT:
            return

        if not self.thread.is_alive():
            self._propogate_state(external_state.RUNNING)
            self.thread.start()

    def thread_resume(self):
        self._propogate_state(external_state.RUNNING)

    def thread_wait(self):
        if _debug:
            self._log.debug("Waiting for the condition lock %s" % threading.current_thread())

        with self.cond:
            while self.state == external_state.RUNNING:
                self.cond.wait()

            if _debug:
                if self.state == external_state.EXITED:
                    self._log.debug("Thread %s has exited from %s" % (self.thread, threading.current_thread()))
                elif self.state == external_state.PAUSED:
                    self._log.debug("Thread %s has called yield from %s"  % (self.thread, threading.current_thread()))
                elif self.state == external_state.RUNNING:
                    self._log.debug("Thread %s is in RUNNING from %d"  % (self.thread, threading.current_thread()))

            if self.state == external_state.INIT:
                raise Exception("Thread %s state was not allowed from %s"  % (self.thread, threading.current_thread()))

        return self.state

class Scheduler(object):
    """The main scheduler.

    Here we accept callbacks from the simulator and schedule the appropriate
    coroutines.

    A callback fires, causing the :any:`react` method to be called, with the
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
    _timer1 = Timer(1)

    def __init__(self):

        self.log = SimLog("cocotb.scheduler")
        if _debug:
            self.log.setLevel(logging.DEBUG)

        # Use OrderedDict here for deterministic behavior (gh-934)

        # A dictionary of pending coroutines for each trigger,
        # indexed by trigger
        self._trigger2coros = collections.OrderedDict()

        # A dictionary mapping coroutines to the trigger they are waiting for
        self._coro2trigger = collections.OrderedDict()

        # Our main state
        self._mode = Scheduler._MODE_NORMAL

        # A dictionary of pending writes
        self._writes = collections.OrderedDict()

        self._pending_coros = []
        self._pending_triggers = []
        self._pending_threads = []
        self._pending_events = []   # Events we need to call set on once we've unwound

        self._terminate = False
        self._test_result = None
        self._entrypoint = None
        self._main_thread = threading.current_thread()

        self._is_reacting = False

        self._write_coro_inst = None
        self._writes_pending = Event()

    @cocotb.decorators.coroutine
    def _do_writes(self):
        """ An internal coroutine that performs pending writes """
        while True:
            yield self._writes_pending.wait()
            if self._mode != Scheduler._MODE_NORMAL:
                yield NextTimeStep()

            yield ReadWrite()

            while self._writes:
                handle, value = self._writes.popitem()
                handle.setimmediatevalue(value)
            self._writes_pending.clear()

    def _check_termination(self):
        """
        Handle a termination that causes us to move onto the next test.
        """
        if self._terminate:
            if _debug:
                self.log.debug("Test terminating, scheduling Timer")

            if self._write_coro_inst is not None:
                self._write_coro_inst.kill()
                self._write_coro_inst = None

            for t in self._trigger2coros:
                t.unprime()

            if self._timer1.primed:
                self._timer1.unprime()

            self._timer1.prime(self.begin_test)
            self._trigger2coros = collections.OrderedDict()
            self._coro2trigger = collections.OrderedDict()
            self._terminate = False
            self._writes = collections.OrderedDict()
            self._writes_pending.clear()
            self._mode = Scheduler._MODE_TERM

    def begin_test(self, trigger=None):
        """Called to initiate a test.

        Could be called on start-up or from a callback.
        """
        if _debug:
            self.log.debug("begin_test called with trigger: %s" %
                           (str(trigger)))
        if _profiling:
            ps = pstats.Stats(_profile).sort_stats('cumulative')
            ps.dump_stats("test_profile.pstat")
            ctx = profiling_context()
        else:
            ctx = nullcontext()

        with ctx:
            self._mode = Scheduler._MODE_NORMAL
            if trigger is not None:
                trigger.unprime()

            # Issue previous test result, if there is one
            if self._test_result is not None:
                if _debug:
                    self.log.debug("Issue test result to regression object")
                cocotb.regression_manager.handle_result(self._test_result)
                self._test_result = None
            if self._entrypoint is not None:
                test = self._entrypoint
                self._entrypoint = None
                self.schedule(test)
                self._check_termination()

    def react(self, trigger):
        """
        Called when a trigger fires.

        We ensure that we only start the event loop once, rather than
        letting it recurse.
        """
        if self._is_reacting:
            # queue up the trigger, the event loop will get to it
            self._pending_triggers.append(trigger)
            return

        assert not self._pending_triggers

        # start the event loop
        self._is_reacting = True
        try:
            self._event_loop(trigger)
        finally:
            self._is_reacting = False


    def _event_loop(self, trigger):
        """
        Run an event loop triggered by the given trigger.

        The loop will keep running until no further triggers fire.

        This should be triggered by only:
        * The beginning of a test, when there is no trigger to react to
        * A GPI trigger
        """
        if _profiling:
            ctx = profiling_context()
        else:
            ctx = nullcontext()

        with ctx:
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

            # work through triggers one by one
            is_first = True
            self._pending_triggers.append(trigger)
            while self._pending_triggers:
                trigger = self._pending_triggers.pop(0)

                if not is_first and isinstance(trigger, GPITrigger):
                    self.log.warning(
                        "A GPI trigger occurred after entering react - this "
                        "should not happen."
                    )
                    assert False

                # this only exists to enable the warning above
                is_first = False

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

                    continue

                # Scheduled coroutines may append to our waiting list so the first
                # thing to do is pop all entries waiting on this trigger.
                scheduling = self._trigger2coros.pop(trigger)

                if _debug:
                    debugstr = "\n\t".join([coro.__name__ for coro in scheduling])
                    if len(scheduling):
                        debugstr = "\n\t" + debugstr
                    self.log.debug("%d pending coroutines for event %s%s" %
                                   (len(scheduling), str(trigger), debugstr))

                # This trigger isn't needed any more
                trigger.unprime()

                for coro in scheduling:
                    if _debug:
                        self.log.debug("Scheduling coroutine %s" % (coro.__name__))
                    self.schedule(coro, trigger=trigger)
                    if _debug:
                        self.log.debug("Scheduled coroutine %s" % (coro.__name__))

                # Schedule may have queued up some events so we'll burn through those
                while self._pending_events:
                    if _debug:
                        self.log.debug("Scheduling pending event %s" %
                                       (str(self._pending_events[0])))
                    self._pending_events.pop(0).set()

            # no more pending triggers
            self._check_termination()
            if _debug:
                self.log.debug("All coroutines scheduled, handing control back"
                               " to simulator")


    def unschedule(self, coro):
        """Unschedule a coroutine.  Unprime any pending triggers"""

        # Unprime the trigger this coroutine is waiting on
        try:
            trigger = self._coro2trigger.pop(coro)
        except KeyError:
            # coroutine probably finished
            pass
        else:
            if coro in self._trigger2coros.setdefault(trigger, []):
                self._trigger2coros[trigger].remove(coro)
            if not self._trigger2coros[trigger]:
                trigger.unprime()
                del self._trigger2coros[trigger]

        if Join(coro) in self._trigger2coros:
            self.react(Join(coro))
        else:
            try:
                # throws an error if the background coroutine errored
                # and no one was monitoring it
                coro.retval
            except TestComplete as test_result:
                self.log.debug("TestComplete received: {}".format(test_result.__class__.__name__))
                self.finish_test(test_result)
            except Exception as e:
                self.finish_test(create_error(self, "Forked coroutine {} raised exception: {}".format(coro, e)))

    def save_write(self, handle, value):
        if self._mode == Scheduler._MODE_READONLY:
            raise Exception("Write to object {0} was scheduled during a read-only sync phase.".format(handle._name))

        # TODO: we should be able to better keep track of when this needs to
        # be scheduled
        if self._write_coro_inst is None:
            self._write_coro_inst = self._do_writes()
            self.schedule(self._write_coro_inst)

        self._writes[handle] = value
        self._writes_pending.set()

    def _coroutine_yielded(self, coro, trigger):
        """Prime the trigger and update our internal mappings."""
        self._coro2trigger[coro] = trigger

        trigger_coros = self._trigger2coros.setdefault(trigger, [])
        if coro is self._write_coro_inst:
            # Our internal write coroutine always runs before any user coroutines.
            # This preserves the behavior prior to the refactoring of writes to
            # this coroutine.
            trigger_coros.insert(0, coro)
        else:
            # Everything else joins the back of the queue
            trigger_coros.append(coro)

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

    def queue_function(self, coroutine):
        """Queue a coroutine for execution and move the containing thread
        so that it does not block execution of the main thread any longer.
        """
        # We should be able to find ourselves inside the _pending_threads list
        matching_threads = [
            t
            for t in self._pending_threads
            if t.thread == threading.current_thread()
        ]
        if len(matching_threads) == 0:
            raise RuntimeError("queue_function called from unrecognized thread")

        # Raises if there is more than one match. This can never happen, since
        # each entry always has a unique thread.
        t, = matching_threads

        t.thread_suspend()
        self._pending_coros.append(coroutine)
        return t

    def run_in_executor(self, func, *args, **kwargs):
        """Run the coroutine in a separate execution thread
        and return a yieldable object for the caller.
        """
        # Create a thread
        # Create a trigger that is called as a result of the thread finishing
        # Create an Event object that the caller can yield on
        # Event object set when the thread finishes execution, this blocks the
        #   calling coroutine (but not the thread) until the external completes

        def execute_external(func, _waiter):
            _waiter._outcome = outcomes.capture(func, *args, **kwargs)
            if _debug:
                self.log.debug("Execution of external routine done %s" % threading.current_thread())
            _waiter.thread_done()

        waiter = external_waiter()
        thread = threading.Thread(group=None, target=execute_external,
                                  name=func.__name__ + "_thread",
                                  args=([func, waiter]), kwargs={})

        waiter.thread = thread
        self._pending_threads.append(waiter)

        return waiter

    def add(self, coroutine):
        """Add a new coroutine.

        Just a wrapper around self.schedule which provides some debug and
        useful error messages in the event of common gotchas.
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
        self._check_termination()
        return coroutine

    def new_test(self, coroutine):
        self._entrypoint = coroutine

    def schedule(self, coroutine, trigger=None):
        """Schedule a coroutine by calling the send method.

        Args:
            coroutine (cocotb.decorators.coroutine): The coroutine to schedule.
            trigger (cocotb.triggers.Trigger): The trigger that caused this
                coroutine to be scheduled.
        """
        if trigger is None:
            send_outcome = outcomes.Value(None)
        else:
            send_outcome = trigger._outcome
        if _debug:
            self.log.debug("Scheduling with {}".format(send_outcome))

        try:
            result = coroutine._advance(send_outcome)
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

        # Normal coroutine completion
        except cocotb.decorators.CoroutineComplete as exc:
            if _debug:
                self.log.debug("Coroutine completed: %s" % str(coroutine))
            self.unschedule(coroutine)
            return

        # Don't handle the result if we're shutting down
        if self._terminate:
            return

        # convert lists into `First` Waitables.
        if isinstance(result, list):
            result = cocotb.triggers.First(*result)

        # convert waitables into coroutines
        if isinstance(result, cocotb.triggers.Waitable):
            result = result._wait()

        # convert coroutinues into triggers
        if isinstance(result, cocotb.decorators.RunningCoroutine):
            if not result.has_started():
                self.queue(result)
                if _debug:
                    self.log.debug("Scheduling nested coroutine: %s" %
                                   result.__name__)
            else:
                if _debug:
                    self.log.debug("Joining to already running coroutine: %s" %
                                   result.__name__)

            result = result.join()

        if isinstance(result, Trigger):
            if _debug:
                self.log.debug("%s: is instance of Trigger" % result)
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

        # We do not return from here until pending threads have completed, but only
        # from the main thread, this seems like it could be problematic in cases
        # where a sim might change what this thread is.
        def unblock_event(ext):
            @cocotb.coroutine
            def wrapper():
                ext.event.set()
                yield PythonTrigger()

        if self._main_thread is threading.current_thread():

            for ext in self._pending_threads:
                ext.thread_start()
                if _debug:
                    self.log.debug("Blocking from %s on %s" % (threading.current_thread(), ext.thread))
                state = ext.thread_wait()
                if _debug:
                    self.log.debug("Back from wait on self %s with newstate %d" % (threading.current_thread(), state))
                if state == external_state.EXITED:
                    self._pending_threads.remove(ext)
                    self._pending_events.append(ext.event)

        # Handle any newly queued coroutines that need to be scheduled
        while self._pending_coros:
            self.add(self._pending_coros.pop(0))

    def finish_test(self, test_result):
        """Cache the test result and set the terminate flag."""
        self.log.debug("finish_test called with %s" % (repr(test_result)))
        if not self._terminate:
            self._terminate = True
            self._test_result = test_result
            self.cleanup()

    def finish_scheduler(self, test_result):
        """Directly call into the regression manager and end test
           once we return the sim will close us so no cleanup is needed.
        """
        self.log.debug("Issue sim closedown result to regression object")
        cocotb.regression_manager.handle_result(test_result)

    def cleanup(self):
        """Clear up all our state.

        Unprime all pending triggers and kill off any coroutines stop all externals.
        """
        # copy since we modify this in kill
        items = list(self._trigger2coros.items())

        # reversing seems to fix gh-928, although the order is still somewhat
        # arbitrary.
        for trigger, waiting in items[::-1]:
            for coro in waiting:
                if _debug:
                    self.log.debug("Killing %s" % str(coro))
                coro.kill()

        if self._main_thread is not threading.current_thread():
            raise Exception("Cleanup() called outside of the main thread")

        for ext in self._pending_threads:
            self.log.warn("Waiting for %s to exit", ext.thread)
