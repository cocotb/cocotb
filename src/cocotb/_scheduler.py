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


import logging
import os
from typing import Any, Callable, List

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


class CallbackHandle:
    def __init__(self, func: Callable[..., Any], args: Any) -> None:
        self._func = func
        self._args = args
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _run(self) -> None:
        self._func(*self._args)


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

    def __init__(self) -> None:
        self._log = logging.getLogger("cocotb.scheduler")
        if _debug:
            self._log.setLevel(logging.DEBUG)
        self._scheduled_tasks: List[CallbackHandle] = []

    def run(self) -> None:
        """Run the main event loop."""
        while self._scheduled_tasks:
            handle = self._scheduled_tasks.pop(0)
            if not handle._cancelled:
                handle._run()

    def schedule(self, func: Callable[..., Any], *args: Any) -> CallbackHandle:
        """Schedule a function to run."""
        handle = CallbackHandle(func, args)
        self._scheduled_tasks.append(handle)
        return handle


instance: Scheduler
