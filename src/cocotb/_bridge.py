# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import functools
import logging
import threading
from typing import Any, Callable, Coroutine, TypeVar

import cocotb
from cocotb.event_loop import _debug
from cocotb.triggers import Event

Result = TypeVar("Result")


def resume(func: Callable[..., Coroutine[Any, Any, Result]]) -> Callable[..., Result]:
    """Converts a coroutine function into a blocking function.

    This allows a :term:`coroutine function` that awaits cocotb triggers to be
    called from a :term:`blocking function` converted by :func:`cocotb.bridge`.
    This completes the bridge through non-:keyword:`async` code.

    When a converted coroutine function is called the current function blocks until the
    converted function exits.

    Results of the converted function are returned from the function call.

    Args:
        func: The :term:`coroutine function` to convert into a :term:`blocking function`.

    Returns:
        *func* as a :term:`blocking function`.

    Raises:
        RuntimeError:
            If the function that is returned is subsequently called from a
            thread that was not started with :class:`cocotb.bridge`.

    .. versionchanged:: 2.0
        Renamed from ``function``.
        No longer implemented as a type.
        The ``log`` attribute is no longer available.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return cocotb._scheduler_inst._queue_function(func(*args, **kwargs))

    return wrapper


def bridge(func: Callable[..., Result]) -> Callable[..., Coroutine[Any, Any, Result]]:
    r"""Converts a blocking function into a coroutine function.

    This function converts a :term:`blocking function` into a :term:`coroutine function`
    with the expectation that the function being converted is intended to call a
    :func:`cocotb.resume` converted function. This creates a bridge through
    non-:keyword:`async` code for code wanting to eventually :keyword:`await` on cocotb
    triggers.

    When a converted function call is used in an :keyword:`await` statement, the current
    Task blocks until the converted function finishes.

    Results of the converted function are returned from the :keyword:`await` expression.

    .. warning::
        Each bridge is implemented with a distinct thread, meaning that all bridges and
        the main thread that runs all :keyword:`async` code are susceptible to races
        when sharing data.

    .. note::
        Bridge threads *must* either finish or block on a :func:`cocotb.resume`
        converted function before control is given back to the simulator.
        This is done to prevent any code from executing in parallel with the simulation.

    Args:
        func: The :term:`blocking function` to convert into a :term:`coroutine function`.

    Returns:
        *func* as a :term:`coroutine function`.

    .. versionchanged:: 2.0
        Renamed from ``external``.
        No longer implemented as a type.
        The ``log`` attribute is no longer available.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return cocotb._scheduler_inst._run_in_executor(func, *args, **kwargs)

    return wrapper


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

    # def _queue_function(self, task):
    #     """Queue a task for execution and move the containing thread
    #     so that it does not block execution of the main thread any longer.
    #     """
    #     # We should be able to find ourselves inside the _pending_threads list
    #     matching_threads = [
    #         t for t in self._pending_threads if t.thread == threading.current_thread()
    #     ]
    #     if len(matching_threads) == 0:
    #         raise RuntimeError("queue_function called from unrecognized thread")

    #     # Raises if there is more than one match. This can never happen, since
    #     # each entry always has a unique thread.
    #     (t,) = matching_threads

    #     async def wrapper():
    #         # This function runs in the scheduler thread
    #         try:
    #             _outcome = _outcomes.Value(await task)
    #         except BaseException as e:
    #             _outcome = _outcomes.Error(e)
    #         event.outcome = _outcome
    #         # Notify the current (scheduler) thread that we are about to wake
    #         # up the background (`@external`) thread, making sure to do so
    #         # before the background thread gets a chance to go back to sleep by
    #         # calling thread_suspend.
    #         # We need to do this here in the scheduler thread so that no more
    #         # tasks run until the background thread goes back to sleep.
    #         t.thread_resume()
    #         event.set()

    #     event = threading.Event()
    #     self._schedule_task(Task(wrapper()))
    #     # The scheduler thread blocks in `thread_wait`, and is woken when we
    #     # call `thread_suspend` - so we need to make sure the task is
    #     # queued before that.
    #     t.thread_suspend()
    #     # This blocks the calling `@external` thread until the task finishes
    #     event.wait()
    #     return event.outcome.get()

    # def _run_in_executor(self, func, *args, **kwargs):
    #     """Run the task in a separate execution thread
    #     and return an awaitable object for the caller.
    #     """
    #     # Create a thread
    #     # Create a trigger that is called as a result of the thread finishing
    #     # Create an Event object that the caller can await on
    #     # Event object set when the thread finishes execution, this blocks the
    #     # calling task (but not the thread) until the external completes

    #     def execute_external(func, _waiter):
    #         _waiter._outcome = _outcomes.capture(func, *args, **kwargs)
    #         if _debug:
    #             self.log.debug(
    #                 f"Execution of external routine done {threading.current_thread()}"
    #             )
    #         _waiter.thread_done()

    #     async def wrapper():
    #         waiter = external_waiter()
    #         thread = threading.Thread(
    #             group=None,
    #             target=execute_external,
    #             name=func.__qualname__ + "_thread",
    #             args=([func, waiter]),
    #             kwargs={},
    #         )

    #         waiter.thread = thread
    #         self._pending_threads.append(waiter)

    #         await waiter.event.wait()

    #         return waiter.result  # raises if there was an exception

    #     return wrapper()

    #     # Schedule may have queued up some events so we'll burn through those
    #     while self._pending_events:
    #         if _debug:
    #             self.log.debug(
    #                 f"Scheduling pending event {self._pending_events[0]}"
    #             )
    #         self._pending_events.pop(0).set()

    # # no more pending tasks
    # if self._terminate:
    #     self._handle_termination()
    # elif _debug:
    #     self.log.debug("All tasks scheduled, handing control back to simulator")
