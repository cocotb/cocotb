#!/usr/bin/env python

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
    Coroutine scheduler.
"""
import types
import threading
import collections
import os
import logging

import simulator
import cocotb
import cocotb.decorators
from cocotb.triggers import Trigger, Timer, ReadOnly, NextTimeStep, ReadWrite


class Scheduler(object):

    def __init__(self):
        self.waiting = collections.defaultdict(list)
        self.log = logging.getLogger("cocotb.scheduler")
        self.writes = {}
        self.writes_lock = threading.RLock()
        self._remove = []
        self._pending_adds = []
        self._startpoint = None
        self._terminate = False
        self._test_result = None
        self._readonly = None
        self._restart = None
        self._restart_coro = None
        # Keep this last
        self._readwrite = self.add(self.move_to_rw())

    def react(self, trigger):
        """
        React called when a trigger fires.  We find any coroutines that are waiting on the particular
            trigger and schedule them.
        """
        trigger.log.debug("Fired!")

        if trigger not in self.waiting:
            # This isn't actually an error - often might do event.set() without knowing
            # whether any coroutines are actually waiting on this event
            # NB should catch a GPI trigger cause that would be catestrophic
            self.log.debug("Not waiting on triggger that fired! (%s)" % (str(trigger)))
            return

        # Scheduled coroutines may append to our waiting list
        # so the first thing to do is pop all entries waiting
        # on this trigger.
        self._scheduling = self.waiting.pop(trigger)
        to_run = len(self._scheduling)

        self.log.debug("%d pending coroutines for event %s" % (to_run, trigger))

        while self._scheduling:
            coroutine = self._scheduling.pop(0)
            del_list = trigger.clearpeers()
            while del_list:
                self.remove(del_list.pop(0))
            self.schedule(coroutine, trigger=trigger)
            self.log.debug("Scheduled coroutine %s" % (coroutine.__name__))

        self.log.debug("Completed scheduling loop, still waiting on:")

        for trig, routines in self.waiting.items():
            self.log.debug("\t%s: [%s]" % (str(trig).ljust(30), " ".join([routine.__name__ for routine in routines])))

        # If we've performed any writes that are cached then schedule
        # another callback for the read-write part of the sim cycle, but
        # if we are terminating then do not allow another callback to be
        # scheduled
        if len(self.writes) and self._readwrite is None and self._terminate is False:
            self._readwrite = self.add(self.move_to_rw())

        # A request for termination may have happened,
        # This is where we really handle to informing of the
        # regression handler that everything from the current
        # test is done and that it can go on with more
        if self._terminate is True:
            if self._readonly is None:
                self._terminate = False
                if self._startpoint is not None:
                    self.add(self._startpoint)
                    self._startpoint = None
                self._test_result = None

        # If the python has caused any subsequent events to fire we might
        # need to schedule more coroutines before we drop back into the
        # simulator
        if self._terminate is False:
            while self._pending_adds:
                coroutine = self._pending_adds.pop(0)
                self.add(coroutine)

        return

    def playout_writes(self):
        if self.writes:
            while self.writes:
                handle, args = self.writes.popitem()
                handle.setimeadiatevalue(args)


    def save_write(self, handle, args):
        self.writes[handle]=args

    def _add_trigger(self, trigger, coroutine):
        """Adds a new trigger which will cause the coroutine to continue when fired"""
        self.waiting[trigger].append(coroutine)
        trigger.prime(self.react)

    def queue(self, coroutine):
        """Queue a coroutine for execution"""
        self._pending_adds.append(coroutine)

    def add(self, coroutine):
        """Add a new coroutine. Required because we cant send to a just started generator (FIXME)"""
        self.log.debug("Queuing new coroutine %s" % coroutine.__name__)
        self.schedule(coroutine)
        return coroutine

    def new_test(self, coroutine):
        self._startpoint = coroutine

    def remove(self, trigger):
        """Remove a trigger from the list of pending coroutines"""
        self.waiting.pop(trigger)
        trigger.unprime()

    def schedule_remove(self, coroutine, callback):
        """Adds the specified coroutine to the list of routines
           That will be removed at the end of the current loop
        """
        self._remove.append((coroutine, callback))

    def prune_routines(self):
        """
        Process the remove list that can have accumulatad during the
        execution of a parent routine
        """
        restart = None
        restart_coro = None
        while self._remove:
            delroutine, cb = self._remove.pop(0)
            for trigger, waiting in self.waiting.items():
                for coro in waiting:
                    if coro is delroutine:
                        self.log.debug("Trowing into %s" % str(coro))
                        cb()
                        try:
                            result = coro.throw(StopIteration)
                            if result:
                                self._restart = result
                                self._restart_coro = coro
                        except StopIteration: pass
                        self.waiting[trigger].remove(coro)
            # Clean up any triggers that no longer have pending coroutines
            for trigger, waiting in self.waiting.items():
                if not waiting:
                    trigger.unprime()
                    del self.waiting[trigger]

    def schedule(self, coroutine, trigger=None):
        """
        Schedule a coroutine by calling the send method

        Args:
            coroutine (cocotb.decorators.coroutine): The coroutine to schedule

            trigger (cocotb.triggers.Trigger): The trigger that caused this
                                                coroutine to be scheduled
        """

        coroutine.log.debug("Scheduling (%s)" % str(trigger))
        try:
            result = coroutine.send(trigger)
        except cocotb.decorators.CoroutineComplete as exc:
            self.log.debug("Coroutine completed execution with CoroutineComplete: %s" % str(coroutine))

            # Call any pending callbacks that were waiting for this coroutine to exit
            exc()
            return

        # TestComplete indication is game over, tidy up
        except cocotb.decorators.TestComplete as test_result:

            # Tag that close down is needed, save the test_result
            # for later use in cleanup handler
            if self._terminate is False:
                self._terminate = True
                self._test_result = test_result
                self.log.debug("Issue test result to regresssion object")
                cocotb.regression.handle_result(test_result)
                self._readonly = self.add(self.move_to_cleanup())
                self.cleanup()

            self.log.debug("Coroutine completed execution with TestComplete: %s" % str(coroutine))
            return

        # Entries may have been added to the remove list while the
        # coroutine was running, clear these down and deschedule
        # before resuming
        if self._terminate is False:
            self.prune_routines()
        
        if isinstance(result, Trigger):
            self._add_trigger(result, coroutine)
        elif isinstance(result, cocotb.decorators.coroutine):
            self.log.debug("Scheduling nested co-routine: %s" % result.__name__)
            # Queue this routine to schedule when the nested routine exits
            self._add_trigger(result.join(), coroutine)
            if self._terminate is False:
                self.schedule(result)
        elif isinstance(result, list):
            if self._terminate is False:
                for trigger in result:
                    trigger.addpeers(result)
                    self._add_trigger(trigger, coroutine)
        else:
            self.log.warning("Unable to schedule coroutine since it's returning stuff %s" % repr(result))
            self.cleanup()
            cocotb.regression.handle_result(cocotb.decorators.TestCompleteFail())
            
        coroutine.log.debug("Finished sheduling coroutine (%s)" % str(trigger))

    def cleanup(self):
        """ Clear up all our state

            Unprime all pending triggers and kill off any coroutines"""
        for trigger, waiting in self.waiting.items():
            for coro in waiting:
                 self.log.debug("Killing %s" % str(coro))
                 coro.kill()

    @cocotb.decorators.coroutine
    def move_to_cleanup(self):
        yield Timer(1)
        self.prune_routines()
        self._readonly = None
        if self._restart is not None:
            self._add_trigger(self._restart, self._restart_coro)
            self._restart = None
        self.log.debug("Out of delay cleanup")

    @cocotb.decorators.coroutine
    def move_to_rw(self):
        try:
            yield ReadWrite()
            self._readwrite = None
            self.playout_writes()
        except StopIteration:
            self.log.warn("Exception caught in read_rw_handler")
