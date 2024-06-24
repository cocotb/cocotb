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

import inspect
import logging
import os
import threading
import warnings
from collections import OrderedDict
from collections.abc import Coroutine
from contextlib import contextmanager
from typing import Any, Callable, Union

import cocotb
import cocotb.decorators
from cocotb import _py_compat, outcomes
from cocotb._deprecation import deprecated
from cocotb.log import SimLog
from cocotb.result import TestComplete
from cocotb.task import Task
from cocotb.triggers import (
    Event,
    GPITrigger,
    Join,
    NextTimeStep,
    NullTrigger,
    ReadOnly,
    ReadWrite,
    Timer,
    Trigger,
)
from cocotb.utils import remove_traceback_frames

# Debug mode controlled by environment variables
_profiling = "COCOTB_ENABLE_PROFILING" in os.environ
if _profiling:
    import cProfile
    import pstats

    _profile = cProfile.Profile()

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


class InternalError(BaseException):
    """An error internal to scheduler. If you see this, report a bug!"""

    pass


class profiling_context:
    """Context manager that profiles its contents"""

    def __enter__(self):
        _profile.enable()

    def __exit__(self, *excinfo):
        _profile.disable()


class external_state:
    INIT = 0
    RUNNING = 1
    PAUSED = 2
    EXITED = 3


@cocotb.decorators.public
class external_waiter:
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

    def _propagate_state(self, new_state):
        with self.cond:
            if _debug:
                self._log.debug(
                    "Changing state from %d -> %d from %s"
                    % (self.state, new_state, threading.current_thread())
                )
            self.state = new_state
            self.cond.notify()

    def thread_done(self):
        if _debug:
            self._log.debug("Thread finished from %s" % (threading.current_thread()))
        self._propagate_state(external_state.EXITED)

    def thread_suspend(self):
        self._propagate_state(external_state.PAUSED)

    def thread_start(self):
        if self.state > external_state.INIT:
            return

        if not self.thread.is_alive():
            self._propagate_state(external_state.RUNNING)
            self.thread.start()

    def thread_resume(self):
        self._propagate_state(external_state.RUNNING)

    def thread_wait(self):
        if _debug:
            self._log.debug(
                "Waiting for the condition lock %s" % threading.current_thread()
            )

        with self.cond:
            while self.state == external_state.RUNNING:
                self.cond.wait()

            if _debug:
                if self.state == external_state.EXITED:
                    self._log.debug(
                        "Thread {} has exited from {}".format(
                            self.thread, threading.current_thread()
                        )
                    )
                elif self.state == external_state.PAUSED:
                    self._log.debug(
                        "Thread %s has called yield from %s"
                        % (self.thread, threading.current_thread())
                    )
                elif self.state == external_state.RUNNING:
                    self._log.debug(
                        "Thread %s is in RUNNING from %d"
                        % (self.thread, threading.current_thread())
                    )

            if self.state == external_state.INIT:
                raise Exception(
                    "Thread %s state was not allowed from %s"
                    % (self.thread, threading.current_thread())
                )

        return self.state


class Scheduler:
    """The main scheduler.

    Here we accept callbacks from the simulator and schedule the appropriate
    coroutines.

    A callback fires, causing the :any:`react` method to be called, with the
    trigger that caused the callback as the first argument.

    We look up a list of coroutines to schedule (indexed by the trigger) and
    schedule them in turn.

    .. attention::

       Implementors should not depend on the scheduling order!

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
        - Corresponds to ``cbReadOnlySynch`` (VPI) or ``vhpiCbRepEndOfTimeStep``
          (VHPI).  In this state we are not allowed to perform writes.

    Write mode
        - Corresponds to ``cbReadWriteSynch`` (VPI) or ``vhpiCbRepLastKnownDeltaCycle`` (VHPI)
          In this mode we play back all the cached write updates.

    We can legally transition from Normal to Write by registering a :class:`~cocotb.triggers.ReadWrite`
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

    _MODE_NORMAL = 1  # noqa
    _MODE_READONLY = 2  # noqa
    _MODE_WRITE = 3  # noqa
    _MODE_TERM = 4  # noqa

    # Singleton events, recycled to avoid spurious object creation
    _next_time_step = NextTimeStep()
    _read_write = ReadWrite()
    _read_only = ReadOnly()
    _timer1 = Timer(1)

    def __init__(self, handle_result: Callable[[Task], None]) -> None:
        self._handle_result = handle_result

        self.log = SimLog("cocotb.scheduler")
        if _debug:
            self.log.setLevel(logging.DEBUG)

        # Use OrderedDict here for deterministic behavior (gh-934)

        # A dictionary of pending coroutines for each trigger,
        # indexed by trigger
        self._trigger2coros = _py_compat.insertion_ordered_dict()

        # Our main state
        self._mode = Scheduler._MODE_NORMAL

        # A dictionary of pending (write_func, args), keyed by handle.
        # Writes are applied oldest to newest (least recently used).
        # Only the last scheduled write to a particular handle in a timestep is performed.
        self._write_calls = OrderedDict()

        self._pending_coros = []
        self._pending_triggers = []
        self._pending_threads = []
        self._pending_events = []  # Events we need to call set on once we've unwound
        self._scheduling = []

        self._terminate = False
        self._test = None
        self._main_thread = threading.current_thread()

        self._current_task = None

        self._is_reacting = False

        self._write_coro_inst = None
        self._writes_pending = Event()

    async def _do_writes(self):
        """An internal coroutine that performs pending writes"""
        while True:
            await self._writes_pending.wait()
            if self._mode != Scheduler._MODE_NORMAL:
                await self._next_time_step

            await self._read_write

            while self._write_calls:
                handle, (func, args) = self._write_calls.popitem(last=False)
                func(*args)
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

            self._timer1.prime(self._test_completed)
            self._trigger2coros = _py_compat.insertion_ordered_dict()
            self._terminate = False
            self._write_calls = OrderedDict()
            self._writes_pending.clear()
            self._mode = Scheduler._MODE_TERM

    def _test_completed(self, trigger=None):
        """Called after a test and its cleanup have completed"""
        if _debug:
            self.log.debug("_test_completed called with trigger: %s" % (str(trigger)))
        if _profiling:
            ps = pstats.Stats(_profile).sort_stats("cumulative")
            ps.dump_stats("test_profile.pstat")
            ctx = profiling_context()
        else:
            ctx = _py_compat.nullcontext()

        with ctx:
            self._mode = Scheduler._MODE_NORMAL
            if trigger is not None:
                trigger.unprime()

            # extract the current test, and clear it
            test = self._test
            self._test = None
            if test is None:
                raise InternalError("_test_completed called with no active test")
            if test._outcome is None:
                raise InternalError("_test_completed called with an incomplete test")

            # Issue previous test result
            if _debug:
                self.log.debug("Issue test result to regression object")

            # this may schedule another test
            self._handle_result(test)

            # if it did, make sure we handle the test completing
            self._check_termination()

    def react(self, trigger):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._react(trigger)

    def _react(self, trigger):
        """
        Called when a trigger fires.

        We ensure that we only start the event loop once, rather than
        letting it recurse.
        """
        if self._is_reacting:
            # queue up the trigger, the event loop will get to it
            self._pending_triggers.append(trigger)
            return

        if self._pending_triggers:
            raise InternalError(
                "Expected all triggers to be handled but found {}".format(
                    self._pending_triggers
                )
            )

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
            ctx = _py_compat.nullcontext()

        with ctx:
            # When a trigger fires it is unprimed internally
            if _debug:
                self.log.debug("Trigger fired: %s" % str(trigger))
            # trigger.unprime()

            if self._mode == Scheduler._MODE_TERM:
                if _debug:
                    self.log.debug(
                        "Ignoring trigger %s since we're terminating" % str(trigger)
                    )
                return

            if trigger is self._read_only:
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

                # Scheduled coroutines may append to our waiting list so the first
                # thing to do is pop all entries waiting on this trigger.
                try:
                    self._scheduling = self._trigger2coros.pop(trigger)
                except KeyError:
                    # GPI triggers should only be ever pending if there is an
                    # associated coroutine waiting on that trigger, otherwise it would
                    # have been unprimed already
                    if isinstance(trigger, GPITrigger):
                        self.log.critical(
                            "No coroutines waiting on trigger that fired: %s"
                            % str(trigger)
                        )

                        trigger.log.info("I'm the culprit")
                    # For Python triggers this isn't actually an error - we might do
                    # event.set() without knowing whether any coroutines are actually
                    # waiting on this event, for example
                    elif _debug:
                        self.log.debug(
                            "No coroutines waiting on trigger that fired: %s"
                            % str(trigger)
                        )

                    del trigger
                    continue

                if _debug:
                    debugstr = "\n\t".join(
                        [coro._coro.__qualname__ for coro in self._scheduling]
                    )
                    if len(self._scheduling) > 0:
                        debugstr = "\n\t" + debugstr
                    self.log.debug(
                        "%d pending coroutines for event %s%s"
                        % (len(self._scheduling), str(trigger), debugstr)
                    )

                # This trigger isn't needed any more
                trigger.unprime()

                for coro in self._scheduling:
                    if coro._outcome is not None:
                        # coroutine was killed by another coroutine waiting on the same trigger
                        continue
                    if _debug:
                        self.log.debug(
                            "Scheduling coroutine %s" % (coro._coro.__qualname__)
                        )
                    self._schedule(coro, trigger=trigger)
                    if _debug:
                        self.log.debug(
                            "Scheduled coroutine %s" % (coro._coro.__qualname__)
                        )

                    # remove our reference to the objects at the end of each loop,
                    # to try and avoid them being destroyed at a weird time (as
                    # happened in gh-957)
                    del coro

                self._scheduling = []

                # Handle any newly queued coroutines that need to be scheduled
                while self._pending_coros:
                    task = self._pending_coros.pop(0)
                    if _debug:
                        self.log.debug(
                            "Scheduling queued coroutine %s" % (task._coro.__qualname__)
                        )
                    self._schedule(task)
                    if _debug:
                        self.log.debug(
                            "Scheduled queued coroutine %s" % (task._coro.__qualname__)
                        )

                    del task

                # Schedule may have queued up some events so we'll burn through those
                while self._pending_events:
                    if _debug:
                        self.log.debug(
                            "Scheduling pending event %s"
                            % (str(self._pending_events[0]))
                        )
                    self._pending_events.pop(0).set()

                # remove our reference to the objects at the end of each loop,
                # to try and avoid them being destroyed at a weird time (as
                # happened in gh-957)
                del trigger

            # no more pending triggers
            self._check_termination()
            if _debug:
                self.log.debug(
                    "All coroutines scheduled, handing control back" " to simulator"
                )

    def unschedule(self, coro):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._unschedule(coro)

    def _unschedule(self, coro):
        """Unschedule a coroutine.  Unprime any pending triggers"""
        if coro in self._pending_coros:
            assert not coro.has_started()
            self._pending_coros.remove(coro)
            # Close coroutine so there is no RuntimeWarning that it was never awaited
            coro.close()
            return

        # Unprime the trigger this coroutine is waiting on
        trigger = coro._trigger
        if trigger is not None:
            coro._trigger = None
            if coro in self._trigger2coros.setdefault(trigger, []):
                self._trigger2coros[trigger].remove(coro)
            if not self._trigger2coros[trigger]:
                trigger.unprime()
                del self._trigger2coros[trigger]

        assert self._test is not None

        if coro is self._test:
            if _debug:
                self.log.debug(f"Unscheduling test {coro}")

            if not self._terminate:
                self._terminate = True
                self._cleanup()

        elif Join(coro) in self._trigger2coros:
            self._react(Join(coro))
        else:
            try:
                # throws an error if the background coroutine errored
                # and no one was monitoring it
                coro._outcome.get()
            except (TestComplete, AssertionError) as e:
                coro.log.info("Test stopped by this forked coroutine")
                e = remove_traceback_frames(e, ["_unschedule", "get"])
                self._abort_test(e)
            except BaseException as e:
                coro.log.error("Exception raised by this forked coroutine")
                e = remove_traceback_frames(e, ["_unschedule", "get"])
                self._abort_test(e)

    def _schedule_write(self, handle, write_func, *args):
        """Queue `write_func` to be called on the next ReadWrite trigger."""
        if self._mode == Scheduler._MODE_READONLY:
            raise Exception(
                f"Write to object {handle._name} was scheduled during a read-only sync phase."
            )

        # TODO: we should be able to better keep track of when this needs to
        # be scheduled
        if self._write_coro_inst is None:
            self._write_coro_inst = self._add(self._do_writes())

        if handle in self._write_calls:
            del self._write_calls[handle]
        self._write_calls[handle] = (write_func, args)
        self._writes_pending.set()

    def _resume_coro_upon(self, coro, trigger):
        """Schedule `coro` to be resumed when `trigger` fires."""
        coro._trigger = trigger

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
            if trigger_coros != [coro]:
                # should never happen
                raise InternalError(
                    "More than one coroutine waiting on an unprimed trigger"
                )

            try:
                trigger.prime(self._react)
            except Exception as e:
                # discard the trigger we associated, it will never fire
                self._trigger2coros.pop(trigger)

                # replace it with a new trigger that throws back the exception
                self._resume_coro_upon(
                    coro,
                    NullTrigger(
                        name="Trigger.prime() Error", _outcome=outcomes.Error(e)
                    ),
                )

    def queue(self, coroutine):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._queue(coroutine)

    def _queue(self, coroutine):
        """Queue a coroutine for execution"""
        # Don't queue the same coroutine more than once (gh-2503)
        if coroutine not in self._pending_coros:
            self._pending_coros.append(coroutine)

    def queue_function(self, coro):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._queue_function(coro)

    def _queue_function(self, coro):
        """Queue a coroutine for execution and move the containing thread
        so that it does not block execution of the main thread any longer.
        """
        # We should be able to find ourselves inside the _pending_threads list
        matching_threads = [
            t for t in self._pending_threads if t.thread == threading.current_thread()
        ]
        if len(matching_threads) == 0:
            raise RuntimeError("queue_function called from unrecognized thread")

        # Raises if there is more than one match. This can never happen, since
        # each entry always has a unique thread.
        (t,) = matching_threads

        async def wrapper():
            # This function runs in the scheduler thread
            try:
                _outcome = outcomes.Value(await coro)
            except BaseException as e:
                _outcome = outcomes.Error(e)
            event.outcome = _outcome
            # Notify the current (scheduler) thread that we are about to wake
            # up the background (`@external`) thread, making sure to do so
            # before the background thread gets a chance to go back to sleep by
            # calling thread_suspend.
            # We need to do this here in the scheduler thread so that no more
            # coroutines run until the background thread goes back to sleep.
            t.thread_resume()
            event.set()

        event = threading.Event()
        self._pending_coros.append(Task(wrapper()))
        # The scheduler thread blocks in `thread_wait`, and is woken when we
        # call `thread_suspend` - so we need to make sure the coroutine is
        # queued before that.
        t.thread_suspend()
        # This blocks the calling `@external` thread until the coroutine finishes
        event.wait()
        return event.outcome.get()

    def run_in_executor(self, func, *args, **kwargs):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._run_in_executor(func, *args, **kwargs)

    def _run_in_executor(self, func, *args, **kwargs):
        """Run the coroutine in a separate execution thread
        and return an awaitable object for the caller.
        """
        # Create a thread
        # Create a trigger that is called as a result of the thread finishing
        # Create an Event object that the caller can await on
        # Event object set when the thread finishes execution, this blocks the
        #   calling coroutine (but not the thread) until the external completes

        def execute_external(func, _waiter):
            _waiter._outcome = outcomes.capture(func, *args, **kwargs)
            if _debug:
                self.log.debug(
                    "Execution of external routine done %s" % threading.current_thread()
                )
            _waiter.thread_done()

        async def wrapper():
            waiter = external_waiter()
            thread = threading.Thread(
                group=None,
                target=execute_external,
                name=func.__qualname__ + "_thread",
                args=([func, waiter]),
                kwargs={},
            )

            waiter.thread = thread
            self._pending_threads.append(waiter)

            await waiter.event.wait()

            return waiter.result  # raises if there was an exception

        return wrapper()

    @staticmethod
    def create_task(coroutine: Any) -> Task:
        """Check to see if the given object is a schedulable coroutine object and if so, return it."""

        if isinstance(coroutine, Task):
            return coroutine
        if isinstance(coroutine, Coroutine):
            return Task(coroutine)
        if inspect.iscoroutinefunction(coroutine):
            raise TypeError(
                "Coroutine function {} should be called prior to being "
                "scheduled.".format(coroutine)
            )
        if isinstance(coroutine, cocotb.decorators.coroutine):
            raise TypeError(
                "Attempt to schedule a coroutine that hasn't started: {}.\n"
                "Did you forget to add parentheses to the @cocotb.test() "
                "decorator?".format(coroutine)
            )
        if inspect.isasyncgen(coroutine):
            raise TypeError(
                "{} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await.".format(
                    coroutine.__qualname__
                )
            )
        raise TypeError(
            "Attempt to add an object of type {} to the scheduler, which "
            "isn't a coroutine: {!r}\n"
            "Did you forget to use the @cocotb.coroutine decorator?".format(
                type(coroutine), coroutine
            )
        )

    @deprecated("This method is now private.")
    def add(self, coroutine: Union[Task, Coroutine]) -> Task:
        return self._add(coroutine)

    def _add(self, coroutine: Union[Task, Coroutine]) -> Task:
        """Add a new coroutine.

        Just a wrapper around self.schedule which provides some debug and
        useful error messages in the event of common gotchas.
        """

        task = self.create_task(coroutine)

        if _debug:
            self.log.debug("Adding new coroutine %s" % task._coro.__qualname__)

        self._schedule(task)
        self._check_termination()
        return task

    def start_soon(self, coro: Union[Coroutine, Task]) -> Task:
        """
        Schedule a coroutine to be run concurrently, starting after the current coroutine yields control.

        In contrast to :func:`~cocotb.fork` which starts the given coroutine immediately, this function
        starts the given coroutine only after the current coroutine yields control.
        This is useful when the coroutine to be forked has logic before the first
        :keyword:`await` that may not be safe to execute immediately.

        .. versionadded:: 1.5
        """

        task = self.create_task(coro)

        if _debug:
            self.log.debug("Queueing a new coroutine %s" % task._coro.__qualname__)

        self._queue(task)
        return task

    def add_test(self, test_coro):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._add_test(test_coro)

    def _add_test(self, test_coro):
        """Called by the regression manager to queue the next test"""
        if self._test is not None:
            raise InternalError("Test was added while another was in progress")

        self._test = test_coro
        self._resume_coro_upon(
            test_coro,
            NullTrigger(name=f"Start {test_coro!s}", _outcome=outcomes.Value(None)),
        )

    # This collection of functions parses a trigger out of the object
    # that was yielded by a coroutine, converting `list` -> `Waitable`,
    # `Waitable` -> `Task`, `Task` -> `Trigger`.
    # Doing them as separate functions allows us to avoid repeating unnecessary
    # `isinstance` checks.

    def _trigger_from_started_coro(self, result: Task) -> Trigger:
        if _debug:
            self.log.debug(
                "Joining to already running coroutine: %s" % result._coro.__qualname__
            )
        return result.join()

    def _trigger_from_unstarted_coro(self, result: Task) -> Trigger:
        self._queue(result)
        if _debug:
            self.log.debug(
                "Scheduling nested coroutine: %s" % result._coro.__qualname__
            )
        return result.join()

    def _trigger_from_waitable(self, result: cocotb.triggers.Waitable) -> Trigger:
        return self._trigger_from_unstarted_coro(Task(result._wait()))

    def _trigger_from_list(self, result: list) -> Trigger:
        return self._trigger_from_waitable(cocotb.triggers.First(*result))

    def _trigger_from_any(self, result) -> Trigger:
        """Convert a yielded object into a Trigger instance"""
        # note: the order of these can significantly impact performance

        if isinstance(result, Trigger):
            return result

        if isinstance(result, Task):
            if not result.has_started():
                return self._trigger_from_unstarted_coro(result)
            else:
                return self._trigger_from_started_coro(result)

        if inspect.iscoroutine(result):
            return self._trigger_from_unstarted_coro(Task(result))

        if isinstance(result, list):
            return self._trigger_from_list(result)

        if isinstance(result, cocotb.triggers.Waitable):
            return self._trigger_from_waitable(result)

        if inspect.isasyncgen(result):
            raise TypeError(
                "{} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await.".format(
                    result.__qualname__
                )
            )

        raise TypeError(
            "Coroutine yielded an object of type {}, which the scheduler can't "
            "handle: {!r}\n"
            "Did you forget to decorate with @cocotb.coroutine?".format(
                type(result), result
            )
        )

    @contextmanager
    def _task_context(self, task):
        """Context manager for the currently running task."""
        old_task = self._current_task
        self._current_task = task
        try:
            yield
        finally:
            self._current_task = old_task

    def schedule(self, coroutine, trigger=None):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._schedule(coroutine, trigger)

    def _schedule(self, coroutine, trigger=None):
        """Schedule a coroutine by calling the send method.

        Args:
            coroutine (cocotb.decorators.coroutine): The coroutine to schedule.
            trigger (cocotb.triggers.Trigger): The trigger that caused this
                coroutine to be scheduled.
        """
        with self._task_context(coroutine):
            if trigger is None:
                send_outcome = outcomes.Value(None)
            else:
                send_outcome = trigger._outcome
            if _debug:
                self.log.debug(f"Scheduling with {send_outcome}")

            coroutine._trigger = None
            result = coroutine._advance(send_outcome)

            if coroutine.done():
                if _debug:
                    self.log.debug(
                        "Coroutine {} completed with {}".format(
                            coroutine, coroutine._outcome
                        )
                    )
                assert result is None
                self._unschedule(coroutine)

            # Don't handle the result if we're shutting down
            if self._terminate:
                return

            if not coroutine.done():
                if _debug:
                    self.log.debug(
                        "Coroutine %s yielded %s (mode %d)"
                        % (coroutine._coro.__qualname__, str(result), self._mode)
                    )
                try:
                    result = self._trigger_from_any(result)
                except TypeError as exc:
                    # restart this coroutine with an exception object telling it that
                    # it wasn't allowed to yield that
                    result = NullTrigger(_outcome=outcomes.Error(exc))

                self._resume_coro_upon(coroutine, result)

            # We do not return from here until pending threads have completed, but only
            # from the main thread, this seems like it could be problematic in cases
            # where a sim might change what this thread is.

            if self._main_thread is threading.current_thread():
                for ext in self._pending_threads:
                    ext.thread_start()
                    if _debug:
                        self.log.debug(
                            "Blocking from {} on {}".format(
                                threading.current_thread(), ext.thread
                            )
                        )
                    state = ext.thread_wait()
                    if _debug:
                        self.log.debug(
                            "Back from wait on self %s with newstate %d"
                            % (threading.current_thread(), state)
                        )
                    if state == external_state.EXITED:
                        self._pending_threads.remove(ext)
                        self._pending_events.append(ext.event)

    def finish_test(self, exc):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._finish_test(exc)

    def _finish_test(self, exc):
        self._abort_test(exc)
        self._check_termination()

    def _abort_test(self, exc):
        """Force this test to end early, without executing any cleanup.

        This happens when a background task fails, and is consistent with
        how the behavior has always been. In future, we may want to behave
        more gracefully to allow the test body to clean up.

        `exc` is the exception that the test should report as its reason for
        aborting.
        """
        if self._test._outcome is not None:  # pragma: no cover
            raise InternalError("Outcome already has a value, but is being set again.")
        outcome = outcomes.Error(exc)
        if _debug:
            self._test.log.debug(f"outcome forced to {outcome}")
        self._test._outcome = outcome
        self._unschedule(self._test)

    def finish_scheduler(self, exc):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._finish_scheduler(exc)

    def _finish_scheduler(self, exc):
        """Directly call into the regression manager and end test
        once we return the sim will close us so no cleanup is needed.
        """
        # If there is an error during cocotb initialization, self._test may not
        # have been set yet. Don't cause another Python exception here.

        if not self._test.done():
            self.log.debug("Issue sim closedown result to regression object")
            self._abort_test(exc)
            self._handle_result(self._test)

    def cleanup(self):
        """
        .. deprecated:: 1.5
            This function is now private.
        """
        warnings.warn("This function is now private.", DeprecationWarning, stacklevel=2)
        return self._cleanup()

    def _cleanup(self):
        """Clear up all our state.

        Unprime all pending triggers and kill off any coroutines, stop all externals.
        """
        # copy since we modify this in kill
        items = list((k, list(v)) for k, v in self._trigger2coros.items())

        # reversing seems to fix gh-928, although the order is still somewhat
        # arbitrary.
        for trigger, waiting in items[::-1]:
            for coro in waiting:
                if _debug:
                    self.log.debug("Killing %s" % str(coro))
                coro.kill()
        assert not self._trigger2coros

        # if there are coroutines being scheduled when the test ends, kill them (gh-1347)
        for coro in self._scheduling:
            if _debug:
                self.log.debug("Killing %s" % str(coro))
            coro.kill()
        self._scheduling = []

        # cancel outstanding triggers *before* queued coroutines (gh-3270)
        while self._pending_triggers:
            trigger = self._pending_triggers.pop(0)
            if _debug:
                self.log.debug("Unpriming %r", trigger)
            trigger.unprime()
        assert not self._pending_triggers

        # Kill any queued coroutines.
        # We use a while loop because task.kill() calls _unschedule(), which will remove the task from _pending_coros.
        # If that happens a for loop will stop early and then the assert will fail.
        while self._pending_coros:
            # Get first task but leave it in the list so that _unschedule() will correctly close the unstarted coroutine object.
            task = self._pending_coros[0]
            task.kill()

        if self._main_thread is not threading.current_thread():
            raise Exception("Cleanup() called outside of the main thread")

        for ext in self._pending_threads:
            self.log.warning("Waiting for %s to exit", ext.thread)
