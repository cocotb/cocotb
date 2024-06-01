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

"""Task scheduler.

FIXME: We have a problem here. If a task schedules a read-only but we
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
from typing import Any, Callable, Union

import cocotb
from cocotb import _outcomes, _py_compat
from cocotb.result import SimFailure, TestSuccess
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


class external_waiter:
    def __init__(self):
        self._outcome = None
        self.thread = None
        self.event = Event()
        self.state = external_state.INIT
        self.cond = threading.Condition()
        self._log = logging.getLogger(
            f"cocotb.external.thread.{self.thread}.0x{id(self):x}"
        )

    @property
    def result(self):
        return self._outcome.get()

    def _propagate_state(self, new_state):
        with self.cond:
            if _debug:
                self._log.debug(
                    f"Changing state from {self.state} -> {new_state} from {threading.current_thread()}"
                )
            self.state = new_state
            self.cond.notify()

    def thread_done(self):
        if _debug:
            self._log.debug(f"Thread finished from {threading.current_thread()}")
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
                f"Waiting for the condition lock {threading.current_thread()}"
            )

        with self.cond:
            while self.state == external_state.RUNNING:
                self.cond.wait()

            if _debug:
                if self.state == external_state.EXITED:
                    self._log.debug(
                        f"Thread {self.thread} has exited from {threading.current_thread()}"
                    )
                elif self.state == external_state.PAUSED:
                    self._log.debug(
                        f"Thread {self.thread} has called yield from {threading.current_thread()}"
                    )
                elif self.state == external_state.RUNNING:
                    self._log.debug(
                        f"Thread {self.thread} is in RUNNING from {threading.current_thread()}"
                    )

            if self.state == external_state.INIT:
                raise Exception(
                    f"Thread {self.thread} state was not allowed from {threading.current_thread()}"
                )

        return self.state


class Scheduler:
    """The main scheduler.

    Here we accept callbacks from the simulator and schedule the appropriate
    tasks.

    A callback fires, causing the :meth:`_react` method to be called, with the
    trigger that caused the callback as the first argument.

    We look up a list of tasks to schedule (indexed by the trigger) and
    schedule them in turn.

    .. attention::

       Implementors should not depend on the scheduling order!

    Due to the simulator nuances and fun with delta delays we have the
    following modes:

    Normal mode
        - Callbacks cause tasks to be scheduled.
        - Any pending writes are cached and do not happen immediately.

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


    Unless a task has explicitly requested to be scheduled in ReadOnly
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

    def __init__(self, test_complete_cb: Callable[[], None]) -> None:
        self._test_complete_cb = test_complete_cb

        self.log = logging.getLogger("cocotb.scheduler")
        if _debug:
            self.log.setLevel(logging.DEBUG)

        # Use OrderedDict here for deterministic behavior (gh-934)

        # A dictionary of pending tasks for each trigger,
        # indexed by trigger
        self._trigger2tasks = _py_compat.insertion_ordered_dict()

        # Our main state
        self._mode = Scheduler._MODE_NORMAL

        # A dictionary of pending (write_func, args), keyed by handle.
        # Writes are applied oldest to newest (least recently used).
        # Only the last scheduled write to a particular handle in a timestep is performed.
        self._write_calls = OrderedDict()

        self._pending_tasks = []
        self._pending_triggers = []
        self._pending_threads = []
        self._pending_events = []  # Events we need to call set on once we've unwound
        self._scheduling = []

        self._terminate = False
        self._test = None
        self._main_thread = threading.current_thread()

        self._current_task = None

        self._is_reacting = False

        self._write_task = None
        self._writes_pending = Event()

    async def _do_writes(self):
        """An internal task that performs pending writes"""
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

            if self._write_task is not None:
                self._write_task.kill()
                self._write_task = None

            for t in self._trigger2tasks:
                t._unprime()

            if self._timer1._primed:
                self._timer1._unprime()

            self._timer1._prime(self._test_completed)
            self._trigger2tasks = _py_compat.insertion_ordered_dict()
            self._terminate = False
            self._write_calls = OrderedDict()
            self._writes_pending.clear()
            self._mode = Scheduler._MODE_TERM

    def _test_completed(self, trigger=None):
        """Called after a test and its cleanup have completed"""
        if _debug:
            self.log.debug(f"_test_completed called with trigger: {trigger}")
        if _profiling:
            ps = pstats.Stats(_profile).sort_stats("cumulative")
            ps.dump_stats("test_profile.pstat")
            ctx = profiling_context()
        else:
            ctx = _py_compat.nullcontext()

        with ctx:
            self._mode = Scheduler._MODE_NORMAL
            if trigger is not None:
                trigger._unprime()

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
            self._test_complete_cb()

            # if it did, make sure we handle the test completing
            self._check_termination()

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
                f"Expected all triggers to be handled but found {self._pending_triggers}"
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
                self.log.debug(f"Trigger fired: {trigger}")
            # trigger._unprime()

            if self._mode == Scheduler._MODE_TERM:
                if _debug:
                    self.log.debug(
                        f"Ignoring trigger {trigger} since we're terminating"
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

                # When tasks run, they may append to our waiting list so the first
                # thing to do is pop all tasks currently waiting on this trigger.
                try:
                    self._scheduling = self._trigger2tasks.pop(trigger)
                except KeyError:
                    # GPI triggers should only be ever pending if there is an
                    # associated task waiting on that trigger, otherwise it would
                    # have been unprimed already
                    if isinstance(trigger, GPITrigger):
                        self.log.critical(
                            f"No tasks waiting on trigger that fired: {trigger}"
                        )

                        trigger.log.info("I'm the culprit")
                    # For Python triggers this isn't actually an error - we might do
                    # event.set() without knowing whether any tasks are actually
                    # waiting on this event, for example
                    elif _debug:
                        self.log.debug(
                            f"No tasks waiting on trigger that fired: {trigger}"
                        )

                    del trigger
                    continue

                if _debug:
                    debugstr = "\n\t".join([str(task) for task in self._scheduling])
                    if len(self._scheduling) > 0:
                        debugstr = "\n\t" + debugstr
                    self.log.debug(
                        f"{len(self._scheduling)} pending tasks for trigger {trigger}{debugstr}"
                    )

                # This trigger isn't needed any more
                trigger._unprime()

                for task in self._scheduling:
                    if task._outcome is not None:
                        # Task was killed by another task waiting on the same trigger
                        continue
                    if _debug:
                        self.log.debug(f"Scheduling task {task}")
                    self._schedule(task, trigger=trigger)
                    if _debug:
                        self.log.debug(f"Scheduled task {task}")

                    # remove our reference to the objects at the end of each loop,
                    # to try and avoid them being destroyed at a weird time (as
                    # happened in gh-957)
                    del task

                self._scheduling = []

                # Handle any newly queued tasks that need to be scheduled
                while self._pending_tasks:
                    task = self._pending_tasks.pop(0)
                    if _debug:
                        self.log.debug(f"Scheduling queued task {task}")
                    self._schedule(task)
                    if _debug:
                        self.log.debug(f"Scheduled queued task {task}")

                    del task

                # Schedule may have queued up some events so we'll burn through those
                while self._pending_events:
                    if _debug:
                        self.log.debug(
                            f"Scheduling pending event {self._pending_events[0]}"
                        )
                    self._pending_events.pop(0).set()

                # remove our reference to the objects at the end of each loop,
                # to try and avoid them being destroyed at a weird time (as
                # happened in gh-957)
                del trigger

            # no more pending triggers
            self._check_termination()
            if _debug:
                self.log.debug("All tasks scheduled, handing control back to simulator")

    def _unprime_task_trigger(self, task: Task[Any]) -> None:
        trigger = task._trigger
        if trigger is not None:
            task._trigger = None
            if task in self._trigger2tasks.setdefault(trigger, []):
                self._trigger2tasks[trigger].remove(task)
            if not self._trigger2tasks[trigger]:
                trigger._unprime()
                del self._trigger2tasks[trigger]

    def _unschedule(self, task: Task[Any]) -> None:
        """Unschedule a task. Unprime any pending triggers"""
        if _debug:
            self.log.debug(f"Unscheduling {task}")

        if task in self._pending_tasks:
            assert not task.has_started()
            self._pending_tasks.remove(task)
            # Close coroutine so there is no RuntimeWarning that it was never awaited
            task._coro.close()
            return

        self._unprime_task_trigger(task)

        assert self._test is not None

        if task is self._test:
            if _debug:
                self.log.debug(f"Unscheduling test {task}")

            if not self._terminate:
                self._terminate = True
                self._cleanup()

        elif Join(task) in self._trigger2tasks:
            self._react(Join(task))
        else:
            try:
                # throws an error if the background task errored
                # and no one was monitoring it
                task._outcome.get()
            except (TestSuccess, SimFailure, AssertionError) as e:
                task.log.info("Test stopped by this task")
                e = remove_traceback_frames(e, ["_unschedule", "get"])
                self._abort_test(e)
            except BaseException as e:
                task.log.error("Exception raised by this task")
                e = remove_traceback_frames(e, ["_unschedule", "get"])
                warnings.warn(
                    '"Unwatched" tasks that throw exceptions will not cause the test to fail. '
                    "See issue #2664 for more details.",
                    FutureWarning,
                )
                self._abort_test(e)

    def _schedule_write(self, handle, write_func, args):
        """Queue `write_func` to be called on the next ReadWrite trigger."""
        if self._mode == Scheduler._MODE_READONLY:
            raise Exception(
                f"Write to object {handle._name} was scheduled during a read-only sync phase."
            )

        # TODO: we should be able to better keep track of when this needs to
        # be scheduled
        if self._write_task is None:
            self._write_task = self.start_soon(self._do_writes())

        if handle in self._write_calls:
            del self._write_calls[handle]
        self._write_calls[handle] = (write_func, args)
        self._writes_pending.set()

    def _resume_task_upon(self, task, trigger):
        """Schedule `task` to be resumed when `trigger` fires."""

        # unprime existing trigger
        if task._trigger is not None:
            if _debug:
                self.log.debug(
                    f"Unpriming existing trigger ({task._trigger!r}) for task ({task!r}) to set a new trigger ({trigger!r})"
                )
            self._unprime_task_trigger(task)

        task._trigger = trigger

        trigger_tasks = self._trigger2tasks.setdefault(trigger, [])
        if task is self._write_task:
            # Our internal write task always runs before any user tasks.
            # This preserves the behavior prior to the refactoring of
            # putting the writes in this task.
            trigger_tasks.insert(0, task)
        else:
            # Everything else joins the back of the queue
            trigger_tasks.append(task)

        if not trigger._primed:
            if trigger_tasks != [task]:
                # should never happen
                raise InternalError("More than one task waiting on an unprimed trigger")

            try:
                trigger._prime(self._react)
            except Exception as e:
                # discard the trigger we associated, it will never fire
                self._trigger2tasks.pop(trigger)

                # replace it with a new trigger that throws back the exception
                self._resume_task_upon(
                    task,
                    NullTrigger(
                        name="Trigger._prime() Error", outcome=_outcomes.Error(e)
                    ),
                )

    def _queue(self, task):
        """Queue a task for execution"""
        # Don't queue the same task more than once (gh-2503)
        if task not in self._pending_tasks:
            self._pending_tasks.append(task)

    def _queue_function(self, task):
        """Queue a task for execution and move the containing thread
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
                _outcome = _outcomes.Value(await task)
            except BaseException as e:
                _outcome = _outcomes.Error(e)
            event.outcome = _outcome
            # Notify the current (scheduler) thread that we are about to wake
            # up the background (`@external`) thread, making sure to do so
            # before the background thread gets a chance to go back to sleep by
            # calling thread_suspend.
            # We need to do this here in the scheduler thread so that no more
            # tasks run until the background thread goes back to sleep.
            t.thread_resume()
            event.set()

        event = threading.Event()
        self._pending_tasks.append(Task(wrapper()))
        # The scheduler thread blocks in `thread_wait`, and is woken when we
        # call `thread_suspend` - so we need to make sure the task is
        # queued before that.
        t.thread_suspend()
        # This blocks the calling `@external` thread until the task finishes
        event.wait()
        return event.outcome.get()

    def _run_in_executor(self, func, *args, **kwargs):
        """Run the task in a separate execution thread
        and return an awaitable object for the caller.
        """
        # Create a thread
        # Create a trigger that is called as a result of the thread finishing
        # Create an Event object that the caller can await on
        # Event object set when the thread finishes execution, this blocks the
        # calling task (but not the thread) until the external completes

        def execute_external(func, _waiter):
            _waiter._outcome = _outcomes.capture(func, *args, **kwargs)
            if _debug:
                self.log.debug(
                    f"Execution of external routine done {threading.current_thread()}"
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
        """Check to see if the given object is a Task or coroutine and if so, return it as a Task."""

        if isinstance(coroutine, Task):
            return coroutine
        if isinstance(coroutine, Coroutine):
            return Task(coroutine)
        if inspect.iscoroutinefunction(coroutine):
            raise TypeError(
                f"Coroutine function {coroutine} should be called prior to being "
                "scheduled."
            )
        if inspect.isasyncgen(coroutine):
            raise TypeError(
                f"{coroutine.__qualname__} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await."
            )
        raise TypeError(
            f"Attempt to add an object of type {type(coroutine)} to the scheduler, which "
            f"isn't a coroutine: {coroutine!r}\n"
        )

    def start_soon(self, task: Union[Coroutine, Task]) -> Task:
        """
        Schedule a task to be run concurrently, starting after the current task yields control.

        .. versionadded:: 1.5
        """

        task = self.create_task(task)

        if _debug:
            self.log.debug(f"Queueing a new task {task!r}")

        self._queue(task)
        return task

    def _add_test(self, test_task):
        """Called by the regression manager to queue the next test"""
        if self._test is not None:
            raise InternalError("Test was added while another was in progress")

        self._test = test_task
        self._resume_task_upon(
            test_task,
            NullTrigger(name=f"Start {test_task!s}", outcome=_outcomes.Value(None)),
        )

    # This collection of functions parses a trigger out of the object
    # that was yielded by a task, converting `list` -> `Waitable`,
    # `Waitable` -> `Task`, `Task` -> `Trigger`.
    # Doing them as separate functions allows us to avoid repeating unnecessary
    # `isinstance` checks.

    def _trigger_from_started_task(self, result: Task) -> Trigger:
        if _debug:
            self.log.debug(f"Joining to already running task: {result}")
        return result.join()

    def _trigger_from_unstarted_task(self, result: Task) -> Trigger:
        self._queue(result)
        if _debug:
            self.log.debug(f"Scheduling unstarted task: {result!r}")
        return result.join()

    def _trigger_from_waitable(self, result: cocotb.triggers.Waitable) -> Trigger:
        return self._trigger_from_unstarted_task(Task(result._wait()))

    def _trigger_from_any(self, result) -> Trigger:
        """Convert a yielded object into a Trigger instance"""
        # note: the order of these can significantly impact performance

        if isinstance(result, Trigger):
            return result

        if isinstance(result, Task):
            if not result.has_started():
                return self._trigger_from_unstarted_task(result)
            else:
                return self._trigger_from_started_task(result)

        if inspect.iscoroutine(result):
            return self._trigger_from_unstarted_task(Task(result))

        if isinstance(result, cocotb.triggers.Waitable):
            return self._trigger_from_waitable(result)

        if inspect.isasyncgen(result):
            raise TypeError(
                f"{result.__qualname__} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await."
            )

        raise TypeError(
            f"Coroutine yielded an object of type {type(result)}, which the scheduler can't "
            f"handle: {result!r}\n"
        )

    def _schedule(self, task, trigger=None):
        """Schedule a task to execute.

        Args:
            task (cocotb.task.Task): The task to schedule.
            trigger (cocotb.triggers.Trigger): The trigger that caused this
                task to be scheduled.
        """
        if self._current_task is not None:
            raise InternalError("_schedule() called while another Task is executing")
        try:
            self._current_task = task
            if trigger is None:
                send_outcome = _outcomes.Value(None)
            else:
                send_outcome = trigger._outcome
            if _debug:
                self.log.debug(f"Scheduling with {send_outcome}")

            task._trigger = None
            result = task._send(send_outcome)

            if task.done():
                if _debug:
                    self.log.debug(f"{task} completed with {task._outcome}")
                assert result is None
                self._unschedule(task)

            # Don't handle the result if we're shutting down
            if self._terminate:
                return

            if not task.done():
                if _debug:
                    self.log.debug(f"{task!r} yielded {result} (mode {self._mode})")
                try:
                    result = self._trigger_from_any(result)
                except TypeError as exc:
                    # restart this task with an exception object telling it that
                    # it wasn't allowed to yield that
                    result = NullTrigger(outcome=_outcomes.Error(exc))

                self._resume_task_upon(task, result)

            # We do not return from here until pending threads have completed, but only
            # from the main thread, this seems like it could be problematic in cases
            # where a sim might change what this thread is.

            if self._main_thread is threading.current_thread():
                for ext in self._pending_threads:
                    ext.thread_start()
                    if _debug:
                        self.log.debug(
                            f"Blocking from {threading.current_thread()} on {ext.thread}"
                        )
                    state = ext.thread_wait()
                    if _debug:
                        self.log.debug(
                            f"Back from wait on self {threading.current_thread()} with newstate {state}"
                        )
                    if state == external_state.EXITED:
                        self._pending_threads.remove(ext)
                        self._pending_events.append(ext.event)
        finally:
            self._current_task = None

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
        outcome = _outcomes.Error(exc)
        if _debug:
            self._test.log.debug(f"outcome forced to {outcome}")
        self._test._outcome = outcome
        self._unschedule(self._test)

    def _finish_scheduler(self, exc):
        """Directly call into the regression manager and end test
        once we return the sim will close us so no cleanup is needed.
        """
        # If there is an error during cocotb initialization, self._test may not
        # have been set yet. Don't cause another Python exception here.

        if not self._test.done():
            self.log.debug("Issue sim closedown result to regression object")
            self._abort_test(exc)
            self._test_complete_cb()

    def _cleanup(self) -> None:
        """Clear up all our state.

        Unprime all pending triggers and kill off any coroutines, stop all externals.
        """
        for trigger, waiting in self._trigger2tasks.items():
            for task in waiting:
                if _debug:
                    self.log.debug(f"Cancelling {task}")
                task._shutdown()
            trigger._unprime()
        self._trigger2tasks.clear()

        # if there are coroutines being scheduled when the test ends, kill them (gh-1347)
        for task in self._scheduling:
            if _debug:
                self.log.debug(f"Cancelling {task}")
            task._shutdown()
        self._scheduling = []

        # cancel outstanding triggers *before* queued coroutines (gh-3270)
        for trigger in self._pending_triggers:
            if _debug:
                self.log.debug(f"Unpriming {trigger}")
            trigger._unprime()
        self._pending_triggers.clear()

        # Kill any queued coroutines.
        for task in self._pending_tasks:
            task._shutdown()
        self._pending_tasks.clear()

        if self._main_thread is not threading.current_thread():
            raise Exception("Cleanup() called outside of the main thread")

        for ext in self._pending_threads:
            self.log.warning(f"Waiting for {ext.thread} to exit")
