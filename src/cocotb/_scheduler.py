# Copyright cocotb contributors
# Copyright (c) 2013, 2018 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Task scheduler."""

import logging
from collections import OrderedDict
from typing import Any, Dict, TypeVar, Union

import cocotb
import cocotb._gpi_triggers
import cocotb.handle
from cocotb import debug
from cocotb._base_triggers import Trigger
from cocotb._bridge import run_bridge_threads
from cocotb._exceptions import InternalError
from cocotb._gpi_triggers import (
    GPITrigger,
    NextTimeStep,
    ReadWrite,
)
from cocotb._profiling import profiling_context
from cocotb._py_compat import insertion_ordered_dict
from cocotb.task import Task, _TaskState

T = TypeVar("T")


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

        # A dictionary of pending tasks for each trigger,
        # indexed by trigger
        self._trigger2tasks: Dict[Trigger, list[Task[object]]] = (
            insertion_ordered_dict()
        )

        self._scheduled_tasks: OrderedDict[Task[object], Union[BaseException, None]] = (
            OrderedDict()
        )

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
        if debug.debug:
            self.log.debug("Trigger fired: %s", trigger)

        # find all tasks waiting on trigger that fired
        try:
            scheduling = self._trigger2tasks.pop(trigger)
        except KeyError:
            # GPI triggers should only be ever pending if there is an
            # associated task waiting on that trigger, otherwise it would
            # have been unprimed already
            if isinstance(trigger, GPITrigger):
                self.log.warning(
                    "No tasks waiting on GPITrigger that fired: %s\n"
                    "This is due to an issue with the GPI or a simulator bug.",
                    trigger,
                )
            # For Python triggers this isn't actually an error - we might do
            # event.set() without knowing whether any tasks are actually
            # waiting on this event, for example
            elif debug.debug:
                self.log.debug("No tasks waiting on trigger that fired: %s", trigger)
            return

        if debug.debug:
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

            if debug.debug:
                self.log.debug("Scheduling task %s", task)
            self._resume_task(task, exc)
            if debug.debug:
                self.log.debug("Scheduled task %s", task)

            # remove our reference to the objects at the end of each loop,
            # to try and avoid them being destroyed at a weird time (as
            # happened in gh-957)
            del task

        # no more pending tasks
        if debug.debug:
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
        if task.done():
            raise RuntimeError(
                f"{task} has finished executing and can not be scheduled again. Did you call start_soon() on a finished Task?"
            )
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
                if debug.debug:
                    self.log.debug("%s completed with %s", task, task._outcome)
                assert trigger is None
                self._unschedule(task)

            if not task.done():
                if debug.debug:
                    self.log.debug("%r yielded %s", task, trigger)
                if not isinstance(trigger, Trigger):
                    e = TypeError(
                        f"Coroutine yielded an object of type {type(trigger)}, which the scheduler can't "
                        f"handle: {trigger!r}\n"
                    )
                    self._schedule_task_internal(task, e)
                else:
                    self._schedule_task_upon(task, trigger)

            run_bridge_threads()

        finally:
            self._current_task = None
