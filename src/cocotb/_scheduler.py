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
from typing import Any, Callable, Dict, Union

import cocotb
import cocotb._write_scheduler
from cocotb import _outcomes, _py_compat
from cocotb._profiling import profiling_context
from cocotb._utils import remove_traceback_frames
from cocotb.result import TestSuccess
from cocotb.task import Task
from cocotb.triggers import (
    Event,
    GPITrigger,
    NextTimeStep,
    ReadOnly,
    ReadWrite,
    Trigger,
    _Join,
)

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


class InternalError(BaseException):
    """An error internal to scheduler. If you see this, report a bug!"""


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
        self._log = logging.getLogger(f"cocotb.bridge.{self.thread}.0x{id(self):x}")

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
    """The main Task scheduler.

    How It Generally Works:
        Tasks are `queued` to run in the scheduler with :meth:`_queue`.
        Queueing adds the Task and an Outcome value to :attr:`_pending_tasks`.
        The main scheduling loop is located in :meth:`_event_loop` and loops over the queued Tasks and `schedules` them.
        :meth:`_schedule` schedules a Task -
        continuing its execution from where it previously yielded control -
        by injecting the Outcome value associated with the Task from the queue.
        The Task's body will run until it finishes or reaches the next ``await`` statement.
        If a Task reaches an ``await``, :meth:`_schedule` will convert the value yielded from the Task into a Trigger with :meth:`_trigger_from_any` and its friend methods.
        Triggers are then `primed` (with :meth:`~cocotb.triggers.Trigger._prime`)
        with a `react` function (:meth:`_sim_react` or :meth:`_react)
        so as to wake up Tasks waiting for that Trigger to `fire` (when the event encoded by the Trigger occurs).
        This is accomplished by :meth:`_resume_task_upon`.
        :meth:`_resume_task_upon` also associates the Trigger with the Task waiting on it to fire by adding them to the :attr:`_trigger2tasks` map.
        If, instead of reaching an ``await``, a Task finishes, :meth:`_schedule` will cause the :class:`~cocotb.triggers.Join` trigger to fire.
        Once a Trigger fires it calls the react function which queues all Tasks waiting for that Trigger to fire.
        Then the process repeats.

        When a Task is cancelled (:meth:`_unschedule`), it is removed from the Task queue if it is currently queued.
        Also, the Task and Trigger are deassociated in the :attr:`_trigger2tasks` map.
        If the cancelled Task is the last Task waiting on a Trigger, that Trigger is `unprimed` to prevent it from firing.

    Simulator Phases:
        All GPITriggers (triggers that are fired by the simulator) go through :meth:`_sim_react`
        which looks at the fired GPITriggers to determine and track the current simulator phase cocotb is executing in.

        Normal phase:
            Corresponds to all non-ReadWrite and non-ReadOnly phases.
            Any writes are cached for the next ReadWrite phase and do not happen immediately.
            Scheduling :class:`~cocotb.triggers.ReadWrite` and :class:`~cocotb.triggers.ReadOnly` are valid.

        ReadWrite phase:
            Corresponds to ``cbReadWriteSynch`` (VPI) or ``vhpiCbRepLastKnownDeltaCycle`` (VHPI).
            At the start of scheduling in this phase we play back all the *previously* cached write updates.
            Any writes are cached for the next ReadWrite phase and do not happen immediately.
            Scheduling :class:`~cocotb.triggers.ReadWrite` and :class:`~cocotb.triggers.ReadOnly` are valid.
            One caveat is that scheduling a :class:`~cocotb.triggers.ReadWrite` while in this phase may not be valid.
            If there were no writes applied at the beginning of this phase, there will be no more events in this time step,
            and there will not be another ReadWrite phase in this time step.
            Simulators generally handle this caveat gracefully by leaving you in the ReadWrite phase of the next time step.

        ReadOnly phase
            Corresponds to ``cbReadOnlySynch`` (VPI) or ``vhpiCbRepEndOfTimeStep`` (VHPI).
            In this state we are not allowed to perform writes.
            Scheduling :class:`~cocotb.triggers.ReadWrite` and :class:`~cocotb.triggers.ReadOnly` are *not* valid.

    Caveats and Special Cases:
        The scheduler treats Tests specially.
        If a Test finishes or a Task ends with an Exception, the scheduler is put into a `terminating` state.
        All currently queued Tasks are cancelled and all pending Triggers are unprimed.
        This is currently spread out between :meth:`_handle_termination` and :meth:`_cleanup`.
        In that mix of functions, the :attr:`_test_complete_cb` callback is called to inform whomever (the regression_manager) the test finished.
        The scheduler also is responsible for starting the next Test in the Normal phase by priming a ``Timer(1)`` with the second half of test completion handling.

        The scheduler is currently where simulator time phase is tracked.
        This is mostly because this is where :meth:`_sim_react` is most conveniently located.
        The scheduler can't currently be made independent of simulator-specific code because of the above special cases which have to respect simulator phasing.

        Currently Task cancellation is accomplished with :meth:`Task.kill() <cocotb.task.Task.kill>`.
        This function immediately cancels the Task by re-entering the scheduler.
        This can cause issues if you are trying to cancel the Test Task or the currently executing Task.

        TODO: There are attributes and methods for dealing with "externals", but I'm not quite sure how it all works yet.
    """

    # Singleton events, recycled to avoid spurious object creation
    _next_time_step = NextTimeStep()
    _read_write = ReadWrite()
    _read_only = ReadOnly()
    _none_outcome = _outcomes.Value(None)

    def __init__(self, test_complete_cb: Callable[[], None]) -> None:
        self._test_complete_cb = test_complete_cb

        self.log = logging.getLogger("cocotb.scheduler")
        if _debug:
            self.log.setLevel(logging.DEBUG)

        # A dictionary of pending tasks for each trigger,
        # indexed by trigger
        self._trigger2tasks: Dict[Trigger, list[Task]] = (
            _py_compat.insertion_ordered_dict()
        )

        self._pending_tasks: OrderedDict[Task[Any], _outcomes.Outcome] = OrderedDict()
        self._pending_threads = []
        self._pending_events = []  # Events we need to call set on once we've unwound

        self._terminate = False
        self._test = None
        self._main_thread = threading.current_thread()

        self._current_task = None

    def _handle_termination(self) -> None:
        """
        Handle a termination that causes us to move onto the next test.
        """
        if self._test is None:
            raise InternalError("_handle_termination called with no active test")
        elif self._test._outcome is None:
            raise InternalError("_handle_termination called with an incomplete test")
        elif _debug:
            self.log.debug("Test terminating...")

        # cleanup triggers and tasks
        self._cleanup()

        # clear state
        self._terminate = False
        self._test = None

        # call complete cb, may schedule another test
        self._test_complete_cb()

    def _sim_react(self, trigger: Trigger) -> None:
        """Called when a :class:`~cocotb.triggers.GPITrigger` fires.

        This is often the entry point into Python from the simulator,
        so this function is in charge of enabling profiling.
        It must also track the current simulator time phase,
        and start the unstarted event loop.
        """
        with profiling_context:
            # TODO: move state tracking to global variable
            # and handle this via some kind of trigger-specific Python callback
            if trigger is self._read_write:
                cocotb.sim_phase = cocotb.SimPhase.READ_WRITE
            if trigger is self._read_only:
                cocotb.sim_phase = cocotb.SimPhase.READ_ONLY
            elif isinstance(trigger, GPITrigger):
                cocotb.sim_phase = cocotb.SimPhase.NORMAL

            # apply inertial writes if ReadWrite
            if trigger is self._read_write:
                cocotb._write_scheduler.apply_scheduled_writes()

            self._react(trigger)
            self._event_loop()

    def _react(self, trigger: Trigger) -> None:
        """Called when a :class:`~cocotb.triggers.Trigger` fires.

        Finds all Tasks waiting on the Trigger that fired and queues them.
        """
        if _debug:
            self.log.debug(f"Trigger fired: {trigger}")

        # find all tasks waiting on trigger that fired
        try:
            scheduling = self._trigger2tasks.pop(trigger)
        except KeyError:
            # GPI triggers should only be ever pending if there is an
            # associated task waiting on that trigger, otherwise it would
            # have been unprimed already
            if isinstance(trigger, GPITrigger):
                self.log.critical(f"No tasks waiting on trigger that fired: {trigger}")
                trigger.log.info("I'm the culprit")
            # For Python triggers this isn't actually an error - we might do
            # event.set() without knowing whether any tasks are actually
            # waiting on this event, for example
            elif _debug:
                self.log.debug(f"No tasks waiting on trigger that fired: {trigger}")
            return

        if _debug:
            debugstr = "\n\t".join([str(task) for task in scheduling])
            if len(scheduling) > 0:
                debugstr = "\n\t" + debugstr
            self.log.debug(
                f"{len(scheduling)} pending tasks for trigger {trigger}{debugstr}"
            )

        # queue all tasks to wake up
        for task in scheduling:
            # unset trigger
            task._trigger = None
            self._queue(task)

        # This trigger isn't needed any more
        trigger._unprime()

    def _event_loop(self) -> None:
        """Run the main event loop.

        This should only be started by:
        * The beginning of a test, when there is no trigger to react to
        * A GPI trigger
        """

        while self._pending_tasks and not self._terminate:
            task, outcome = self._pending_tasks.popitem(last=False)

            if _debug:
                self.log.debug(f"Scheduling task {task}")
            self._schedule(task, outcome)
            if _debug:
                self.log.debug(f"Scheduled task {task}")

            # remove our reference to the objects at the end of each loop,
            # to try and avoid them being destroyed at a weird time (as
            # happened in gh-957)
            del task

            # Schedule may have queued up some events so we'll burn through those
            while self._pending_events:
                if _debug:
                    self.log.debug(
                        f"Scheduling pending event {self._pending_events[0]}"
                    )
                self._pending_events.pop(0).set()

        # no more pending tasks
        if self._terminate:
            self._handle_termination()
        elif _debug:
            self.log.debug("All tasks scheduled, handing control back to simulator")

    def _unschedule(self, task: Task[Any]) -> None:
        """Unschedule a task and unprime dangling pending triggers.

        Also:
          * enters the scheduler termination state if the Test Task is unscheduled.
          * creates and fires a :class:`~cocotb.triggers.Join` trigger.
          * forcefully ends the Test if a Task ends with an exception.
        """

        # remove task from queue
        if task in self._pending_tasks:
            self._pending_tasks.pop(task)

        # Unprime the trigger this task is waiting on
        trigger = task._trigger
        if trigger is not None:
            task._trigger = None
            if task in self._trigger2tasks.setdefault(trigger, []):
                self._trigger2tasks[trigger].remove(task)
            if not self._trigger2tasks[trigger]:
                trigger._unprime()
                del self._trigger2tasks[trigger]

        assert self._test is not None

        if task is self._test:
            if _debug:
                self.log.debug(f"Unscheduling test {task}")

            self._terminate = True

        elif _Join(task) in self._trigger2tasks:
            self._react(_Join(task))
        else:
            try:
                # throws an error if the background task errored
                # and no one was monitoring it
                task._outcome.get()
            except (TestSuccess, AssertionError) as e:
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

    def _resume_task_upon(self, task: Task[Any], trigger: Trigger) -> None:
        """Schedule `task` to be resumed when `trigger` fires."""
        task._trigger = trigger

        trigger_tasks = self._trigger2tasks.setdefault(trigger, [])
        trigger_tasks.append(task)

        if not trigger._primed:
            if trigger_tasks != [task]:
                # should never happen
                raise InternalError("More than one task waiting on an unprimed trigger")

            try:
                # TODO maybe associate the react method with the trigger object so
                # we don't have to do a type check here.
                if isinstance(trigger, GPITrigger):
                    trigger._prime(self._sim_react)
                else:
                    trigger._prime(self._react)
            except Exception as e:
                # discard the trigger we associated, it will never fire
                self._trigger2tasks.pop(trigger)

                # replace it with a new trigger that throws back the exception
                self._queue(task, outcome=_outcomes.Error(e))

    def _queue(
        self, task: Task[Any], outcome: _outcomes.Outcome[Any] = _none_outcome
    ) -> None:
        """Queue *task* for scheduling.

        It is an error to attempt to queue a task that has already been queued.
        """
        # Don't queue the same task more than once (gh-2503)
        if task in self._pending_tasks:
            raise InternalError("Task was queued more than once.")
        self._pending_tasks[task] = outcome

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
        self._queue(Task(wrapper()))
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

    def _add_test(self, test_task: Task[None]) -> None:
        """Called by the regression manager to queue the next test"""
        if self._test is not None:
            raise InternalError("Test was added while another was in progress")

        self._test = test_task
        self._queue(test_task)
        self._event_loop()

    # This collection of functions parses a trigger out of the object
    # that was yielded by a task, converting `list` -> `Waitable`,
    # `Waitable` -> `Task`, `Task` -> `Trigger`.
    # Doing them as separate functions allows us to avoid repeating unnecessary
    # `isinstance` checks.

    def _trigger_from_started_task(self, result: Task) -> Trigger:
        if _debug:
            self.log.debug(f"Joining to already running task: {result}")
        return _Join(result)

    def _trigger_from_unstarted_task(self, result: Task) -> Trigger:
        self._queue(result)
        if _debug:
            self.log.debug(f"Scheduling unstarted task: {result!r}")
        return _Join(result)

    def _trigger_from_any(self, result) -> Trigger:
        """Convert a yielded object into a Trigger instance"""
        # note: the order of these can significantly impact performance

        if isinstance(result, Trigger):
            return result

        if isinstance(result, Task):
            if not result.has_started() and result not in self._pending_tasks:
                return self._trigger_from_unstarted_task(result)
            else:
                return self._trigger_from_started_task(result)

        raise TypeError(
            f"Coroutine yielded an object of type {type(result)}, which the scheduler can't "
            f"handle: {result!r}\n"
        )

    def _schedule(self, task: Task, outcome: _outcomes.Outcome[Any]) -> None:
        """Schedule *task* with *outcome*.

        Args:
            task: The task to schedule.
            outcome: The outcome to inject into the *task*.

        Scheduling runs *task* until it either finishes or reaches the next ``await`` statement.
        If *task* completes, it is unscheduled, a Join trigger fires, and test completion is inspected.
        Otherwise, it reached an ``await`` and we have a result object which is converted to a trigger,
        that trigger is primed,
        then that trigger and the *task* are registered with the :attr:`_trigger2tasks` map.
        """
        if self._current_task is not None:
            raise InternalError("_schedule() called while another Task is executing")
        try:
            self._current_task = task

            result = task._advance(outcome=outcome)

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
                    self.log.debug(f"{task!r} yielded {result} ({cocotb.sim_phase})")
                try:
                    result = self._trigger_from_any(result)
                except TypeError as exc:
                    # restart this task with an exception object telling it that
                    # it wasn't allowed to yield that
                    self._queue(task, _outcomes.Error(exc))
                else:
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

    def _cleanup(self) -> None:
        """Clear up all our state.

        Unprime all pending triggers and kill off any tasks, stop all externals.
        """
        # copy since we modify this in kill
        items = list((k, list(v)) for k, v in self._trigger2tasks.items())

        # reversing seems to fix gh-928, although the order is still somewhat
        # arbitrary.
        for _, waiting in items[::-1]:
            for task in waiting:
                if _debug:
                    self.log.debug(f"Killing {task}")
                task.kill()
            # we don't unprime trigger here since removing all tasks waiting on
            # the trigger should cause it to be unprimed in _unschedule
        assert not self._trigger2tasks

        # Kill any queued coroutines.
        # We use a while loop because task.kill() calls _unschedule(), which will remove the task from _pending_tasks.
        # If that happens a for loop will stop early and then the assert will fail.
        while self._pending_tasks:
            task, _ = self._pending_tasks.popitem(last=False)
            task.kill()

        if self._main_thread is not threading.current_thread():
            raise Exception("Cleanup() called outside of the main thread")

        for ext in self._pending_threads:
            self.log.warning(f"Waiting for {ext.thread} to exit")
