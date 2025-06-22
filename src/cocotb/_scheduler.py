#!/usr/bin/env python

# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Task scheduler.

FIXME: We have a problem here. If a task schedules a read-only but we
also have pending writes we have to schedule the ReadWrite callback before
the ReadOnly (and this is invalid, at least in Modelsim).
"""

import logging
import os
import threading
from bdb import BdbQuit
from collections import OrderedDict
from typing import Any, Callable, Coroutine, Dict, List, TypeVar, Union

import cocotb
import cocotb._gpi_triggers
import cocotb.handle
from cocotb._base_triggers import Event, Trigger
from cocotb._bridge import external_state, external_waiter
from cocotb._exceptions import InternalError
from cocotb._gpi_triggers import (
    GPITrigger,
    NextTimeStep,
    ReadWrite,
)
from cocotb._outcomes import Error, Outcome, Value, capture
from cocotb._profiling import profiling_context
from cocotb._py_compat import ParamSpec, insertion_ordered_dict
from cocotb.task import Task, _TaskState

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


T = TypeVar("T")

P = ParamSpec("P")


class Scheduler:
    """The main Task scheduler.

    How It Generally Works:
        Tasks are `queued` to run in the scheduler with :meth:`_queue`.
        Queueing adds the Task and an Outcome value to :attr:`_pending_tasks`.
        The main scheduling loop is located in :meth:`_event_loop` and loops over the queued Tasks and `schedules` them.
        :meth:`_schedule` schedules a Task -
        continuing its execution from where it previously yielded control -
        by injecting the Outcome value associated with the Task from the queue.
        The Task's body will run until it finishes or reaches the next :keyword:`await` statement.
        If a Task reaches an :keyword:`await`, :meth:`_schedule` will convert the value yielded from the Task into a Trigger with :meth:`_trigger_from_any` and its friend methods.
        Triggers are then `primed` (with :meth:`~cocotb.triggers.Trigger._prime`)
        with a `react` function (:meth:`_sim_react` or :meth:`_react)
        so as to wake up Tasks waiting for that Trigger to `fire` (when the event encoded by the Trigger occurs).
        This is accomplished by :meth:`_resume_task_upon`.
        :meth:`_resume_task_upon` also associates the Trigger with the Task waiting on it to fire by adding them to the :attr:`_trigger2tasks` map.
        If, instead of reaching an :keyword:`await`, a Task finishes, :meth:`_schedule` will cause the :class:`~cocotb.task.Join` trigger to fire.
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

    def __init__(self) -> None:
        self.log = logging.getLogger("cocotb.scheduler")
        if _debug:
            self.log.setLevel(logging.DEBUG)

        # A dictionary of pending tasks for each trigger,
        # indexed by trigger
        self._trigger2tasks: Dict[Trigger, list[Task[object]]] = (
            insertion_ordered_dict()
        )

        self._scheduled_tasks: OrderedDict[Task[object], Union[BaseException, None]] = (
            OrderedDict()
        )
        self._pending_threads: List[external_waiter[Any]] = []
        self._pending_events: List[Event] = []

        self._main_thread = threading.current_thread()

        self._current_task: Union[Task[object], None] = None

    def _sim_react(self, trigger: GPITrigger) -> None:
        """Called when a :class:`~cocotb.triggers.GPITrigger` fires.

        This is often the entry point into Python from the simulator,
        so this function is in charge of enabling profiling.
        It must also track the current simulator time phase,
        and start the unstarted event loop.
        """
        with profiling_context:
            # TODO: move state tracking to global variable
            # and handle this via some kind of trigger-specific Python callback
            cocotb._gpi_triggers._current_gpi_trigger = trigger

            # apply inertial writes if ReadWrite
            if trigger is self._read_write:
                cocotb.handle._apply_scheduled_writes()

            self._react(trigger)
            self._event_loop()

    def _react(self, trigger: Trigger) -> None:
        """Called when a :class:`~cocotb.triggers.Trigger` fires.

        Finds all Tasks waiting on the Trigger that fired and queues them.
        """
        if _debug:
            self.log.debug("Trigger fired: %s", trigger)

        # find all tasks waiting on trigger that fired
        try:
            scheduling = self._trigger2tasks.pop(trigger)
        except KeyError:
            # GPI triggers should only be ever pending if there is an
            # associated task waiting on that trigger, otherwise it would
            # have been unprimed already
            if isinstance(trigger, GPITrigger):
                self.log.critical("No tasks waiting on trigger that fired: %s", trigger)
                trigger._log.info("I'm the culprit")
            # For Python triggers this isn't actually an error - we might do
            # event.set() without knowing whether any tasks are actually
            # waiting on this event, for example
            elif _debug:
                self.log.debug("No tasks waiting on trigger that fired: %s", trigger)
            return

        if _debug:
            debugstr = "\n\t".join([str(task) for task in scheduling])
            if len(scheduling) > 0:
                debugstr = "\n\t" + debugstr
            self.log.debug(
                "%d pending tasks for trigger %s%s",
                len(scheduling),
                trigger,
                debugstr,
            )

        # queue all tasks to wake up
        for task in scheduling:
            # unset trigger
            task._trigger = None
            self._schedule_task_internal(task)

        # cleanup trigger
        trigger._cleanup()

    def _event_loop(self) -> None:
        """Run the main event loop.

        This should only be started by:
        * The beginning of a test, when there is no trigger to react to
        * A GPI trigger
        """

        while self._scheduled_tasks:
            task, exc = self._scheduled_tasks.popitem(last=False)

            if _debug:
                self.log.debug("Scheduling task %s", task)
            self._resume_task(task, exc)
            if _debug:
                self.log.debug("Scheduled task %s", task)

            # remove our reference to the objects at the end of each loop,
            # to try and avoid them being destroyed at a weird time (as
            # happened in gh-957)
            del task

            # Schedule may have queued up some events so we'll burn through those
            while self._pending_events:
                if _debug:
                    self.log.debug(
                        "Scheduling pending event %s", self._pending_events[0]
                    )
                self._pending_events.pop(0).set()

        # no more pending tasks
        if _debug:
            self.log.debug("All tasks scheduled, handing control back to simulator")

    def _unschedule(self, task: Task[Any]) -> None:
        """Unschedule a task and unprime dangling pending triggers.

        Also:
          * enters the scheduler termination state if the Test Task is unscheduled.
          * creates and fires a :class:`~cocotb.task.Join` trigger.
          * forcefully ends the Test if a Task ends with an exception.
        """

        # remove task from queue
        if task in self._scheduled_tasks:
            self._scheduled_tasks.pop(task)

        # Unprime the trigger this task is waiting on
        trigger = task._trigger
        if trigger is not None:
            task._trigger = None
            if task in self._trigger2tasks.setdefault(trigger, []):
                self._trigger2tasks[trigger].remove(task)
            if not self._trigger2tasks[trigger]:
                trigger._unprime()
                del self._trigger2tasks[trigger]

    def _schedule_task_upon(self, task: Task[Any], trigger: Trigger) -> None:
        """Schedule `task` to be resumed when `trigger` fires."""
        # TODO Move this all into Task
        task._trigger = trigger
        task._state = _TaskState.PENDING

        trigger_tasks = self._trigger2tasks.setdefault(trigger, [])
        trigger_tasks.append(task)

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
            self._schedule_task_internal(task, e)

    def _schedule_task(self, task: Task[Any]) -> None:
        """Queue *task* for scheduling.

        It is an error to attempt to queue a task that has already been queued.
        """
        if task in self._scheduled_tasks:
            return
        for tasks in self._trigger2tasks.values():
            if task in tasks:
                return
        self._schedule_task_internal(task)

    def _schedule_task_internal(
        self, task: Task[Any], exc: Union[BaseException, None] = None
    ) -> None:
        # TODO Move state tracking into Task
        task._state = _TaskState.SCHEDULED
        self._scheduled_tasks[task] = exc

    def _queue_function(self, task: Coroutine[Trigger, None, T]) -> T:
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

        outcome: Union[Outcome[T], None] = None

        async def wrapper() -> None:
            nonlocal outcome
            # This function runs in the scheduler thread
            try:
                outcome = Value(await task)
            except (KeyboardInterrupt, SystemExit, BdbQuit):
                # Allow these to bubble up to the execution root to fail the sim immediately.
                # This follows asyncio's behavior.
                raise
            except BaseException as e:
                outcome = Error(e)
            # Notify the current (scheduler) thread that we are about to wake
            # up the background (`@external`) thread, making sure to do so
            # before the background thread gets a chance to go back to sleep by
            # calling thread_suspend.
            # We need to do this here in the scheduler thread so that no more
            # tasks run until the background thread goes back to sleep.
            t.thread_resume()
            event.set()

        event = threading.Event()
        self._schedule_task_internal(Task(wrapper()))
        # The scheduler thread blocks in `thread_wait`, and is woken when we
        # call `thread_suspend` - so we need to make sure the task is
        # queued before that.
        t.thread_suspend()
        # This blocks the calling `@external` thread until the task finishes
        event.wait()
        assert outcome is not None
        return outcome.get()

    def _run_in_executor(
        self, func: "Callable[P, T]", *args: "P.args", **kwargs: "P.kwargs"
    ) -> Coroutine[Trigger, None, T]:
        """Run the task in a separate execution thread
        and return an awaitable object for the caller.
        """
        # Create a thread
        # Create a trigger that is called as a result of the thread finishing
        # Create an Event object that the caller can await on
        # Event object set when the thread finishes execution, this blocks the
        # calling task (but not the thread) until the external completes

        waiter = external_waiter[T]()

        def execute_external() -> None:
            waiter._outcome = capture(func, *args, **kwargs)
            if _debug:
                self.log.debug(
                    "Execution of external routine done %s", threading.current_thread()
                )
            waiter.thread_done()

        async def wrapper() -> T:
            thread = threading.Thread(
                group=None,
                target=execute_external,
                name=func.__qualname__ + "_thread",
            )

            waiter.thread = thread
            self._pending_threads.append(waiter)

            await waiter.event.wait()

            return waiter.result  # raises if there was an exception

        return wrapper()

    def _resume_task(self, task: Task[object], exc: Union[BaseException, None]) -> None:
        """Resume *task* with *outcome*.

        Args:
            task: The task to schedule.
            outcome: The outcome to inject into the *task*.

        Scheduling runs *task* until it either finishes or reaches the next :keyword:`await` statement.
        If *task* completes, it is unscheduled, a Join trigger fires, and test completion is inspected.
        Otherwise, it reached an :keyword:`await` and we have a result object which is converted to a trigger,
        that trigger is primed,
        then that trigger and the *task* are registered with the :attr:`_trigger2tasks` map.
        """
        if self._current_task is not None:
            raise InternalError("_schedule() called while another Task is executing")
        try:
            self._current_task = task

            trigger = task._advance(exc)

            if task.done():
                if _debug:
                    self.log.debug("%s completed with %s", task, task._outcome)
                assert trigger is None
                self._unschedule(task)

            if not task.done():
                if _debug:
                    self.log.debug("%r yielded %s", task, trigger)
                if not isinstance(trigger, Trigger):
                    e = TypeError(
                        f"Coroutine yielded an object of type {type(trigger)}, which the scheduler can't "
                        f"handle: {trigger!r}\n"
                    )
                    self._schedule_task_internal(task, e)
                else:
                    self._schedule_task_upon(task, trigger)

            # We do not return from here until pending threads have completed, but only
            # from the main thread, this seems like it could be problematic in cases
            # where a sim might change what this thread is.

            if self._main_thread is threading.current_thread():
                for ext in self._pending_threads:
                    ext.thread_start()
                    if _debug:
                        self.log.debug(
                            "Blocking from %s on %s",
                            threading.current_thread(),
                            ext.thread,
                        )
                    state = ext.thread_wait()
                    if _debug:
                        self.log.debug(
                            "Back from wait on self %s with newstate %s",
                            threading.current_thread(),
                            state,
                        )
                    if state == external_state.EXITED:
                        self._pending_threads.remove(ext)
                        self._pending_events.append(ext.event)
        finally:
            self._current_task = None
