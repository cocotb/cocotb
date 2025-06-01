# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import functools
import logging
import threading
from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    Callable,
    Coroutine,
    Generic,
    TypeVar,
    Union,
)

import cocotb
from cocotb import debug
from cocotb._base_triggers import Event, Trigger
from cocotb._exceptions import InternalError
from cocotb._py_compat import ParamSpec

if TYPE_CHECKING:
    from cocotb._outcomes import Outcome

P = ParamSpec("P")

Result = TypeVar("Result")


def resume(
    func: "Callable[P, Coroutine[Trigger, None, Result]]",
) -> "Callable[P, Result]":
    """Converts a coroutine function into a blocking function.

    This allows a :term:`coroutine function` that awaits cocotb triggers to be
    called from a :term:`blocking function` converted by :func:`.bridge`.
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
            thread that was not started with :class:`.bridge`.

    .. versionchanged:: 2.0
        Renamed from ``function``.
        No longer implemented as a type.
        The ``log`` attribute is no longer available.
    """

    @functools.wraps(func)
    def wrapper(*args: "P.args", **kwargs: "P.kwargs") -> Result:
        return cocotb._scheduler_inst._queue_function(func(*args, **kwargs))

    return wrapper


def bridge(
    func: "Callable[P, Result]",
) -> "Callable[P, Coroutine[Trigger, None, Result]]":
    r"""Converts a blocking function into a coroutine function.

    This function converts a :term:`blocking function` into a :term:`coroutine function`
    with the expectation that the function being converted is intended to call a
    :func:`.resume` converted function. This creates a bridge through
    non-:keyword:`async` code for code wanting to eventually :keyword:`await` on cocotb
    triggers.

    When a converted function call is used in an :keyword:`await` statement, the current
    Task blocks until the converted function finishes.

    Results of the converted function are returned from the :keyword:`await` expression.

    .. note::
        Bridge threads *must* either finish or block on a :func:`.resume`
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
    def wrapper(
        *args: "P.args", **kwargs: "P.kwargs"
    ) -> Coroutine[Trigger, None, Result]:
        return cocotb._scheduler_inst._run_in_executor(func, *args, **kwargs)

    return wrapper


class external_state(IntEnum):
    INIT = 0
    RUNNING = 1
    PAUSED = 2
    EXITED = 3


class external_waiter(Generic[Result]):
    def __init__(self) -> None:
        self._outcome: Union[Outcome[Result], None] = None
        self.thread: threading.Thread
        self.event = Event()
        self.state = external_state.INIT
        self.cond = threading.Condition()
        self._log = logging.getLogger(f"cocotb.bridge.0x{id(self):x}")

    @property
    def result(self) -> Result:
        if self._outcome is None:
            raise InternalError("Got result of external before it finished")
        return self._outcome.get()

    def _propagate_state(self, new_state: external_state) -> None:
        with self.cond:
            if debug.debug:
                self._log.debug(
                    f"Changing state from {self.state} -> {new_state} from {threading.current_thread()}"
                )
            self.state = new_state
            self.cond.notify()

    def thread_done(self) -> None:
        if debug.debug:
            self._log.debug(f"Thread finished from {threading.current_thread()}")
        self._propagate_state(external_state.EXITED)

    def thread_suspend(self) -> None:
        self._propagate_state(external_state.PAUSED)

    def thread_start(self) -> None:
        if self.state > external_state.INIT:
            return

        if not self.thread.is_alive():
            self._propagate_state(external_state.RUNNING)
            self.thread.start()

    def thread_resume(self) -> None:
        self._propagate_state(external_state.RUNNING)

    def thread_wait(self) -> external_state:
        if debug.debug:
            self._log.debug(
                f"Waiting for the condition lock {threading.current_thread()}"
            )

        with self.cond:
            while self.state == external_state.RUNNING:
                self.cond.wait()

            if debug.debug:
                if self.state == external_state.EXITED:
                    self._log.debug(
                        f"Thread {self.thread} has exited from {threading.current_thread()}"
                    )
                elif self.state == external_state.PAUSED:
                    self._log.debug(
                        f"Thread {self.thread} has called yield from {threading.current_thread()}"
                    )

            if self.state == external_state.INIT:
                raise Exception(
                    f"Thread {self.thread} state was not allowed from {threading.current_thread()}"
                )

        return self.state

    # def _queue_function(self, task: Coroutine[Trigger, None, T]) -> T:
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

    #     outcome: Union[Outcome[T], None] = None

    #     async def wrapper() -> None:
    #         nonlocal outcome
    #         # This function runs in the scheduler thread
    #         try:
    #             outcome = Value(await task)
    #         except (KeyboardInterrupt, SystemExit, BdbQuit):
    #             # Allow these to bubble up to the execution root to fail the sim immediately.
    #             # This follows asyncio's behavior.
    #             raise
    #         except BaseException as e:
    #             outcome = Error(e)
    #         # Notify the current (scheduler) thread that we are about to wake
    #         # up the background (`@external`) thread, making sure to do so
    #         # before the background thread gets a chance to go back to sleep by
    #         # calling thread_suspend.
    #         # We need to do this here in the scheduler thread so that no more
    #         # tasks run until the background thread goes back to sleep.
    #         t.thread_resume()
    #         event.set()

    #     event = threading.Event()
    #     self._schedule_task_internal(Task(wrapper()))
    #     # The scheduler thread blocks in `thread_wait`, and is woken when we
    #     # call `thread_suspend` - so we need to make sure the task is
    #     # queued before that.
    #     t.thread_suspend()
    #     # This blocks the calling `@external` thread until the task finishes
    #     event.wait()
    #     assert outcome is not None
    #     return outcome.get()

    # def _run_in_executor(
    #     self, func: "Callable[P, T]", *args: "P.args", **kwargs: "P.kwargs"
    # ) -> Coroutine[Trigger, None, T]:
    #     """Run the task in a separate execution thread
    #     and return an awaitable object for the caller.
    #     """
    #     # Create a thread
    #     # Create a trigger that is called as a result of the thread finishing
    #     # Create an Event object that the caller can await on
    #     # Event object set when the thread finishes execution, this blocks the
    #     # calling task (but not the thread) until the external completes

    #     waiter = external_waiter[T]()

    #     def execute_external() -> None:
    #         waiter._outcome = capture(func, *args, **kwargs)
    #         if DEBUG:
    #             self.log.debug(
    #                 f"Execution of external routine done {threading.current_thread()}"
    #             )
    #         waiter.thread_done()

    #     async def wrapper() -> T:
    #         thread = threading.Thread(
    #             group=None,
    #             target=execute_external,
    #             name=func.__qualname__ + "_thread",
    #         )

    #         waiter.thread = thread
    #         self._pending_threads.append(waiter)

    #         await waiter.event.wait()

    #         return waiter.result  # raises if there was an exception

    #     return wrapper()

    # # We do not return from here until pending threads have completed, but only
    # # from the main thread, this seems like it could be problematic in cases
    # # where a sim might change what this thread is.

    # if self._main_thread is threading.current_thread():
    #     for ext in self._pending_threads:
    #         ext.thread_start()
    #         if DEBUG:
    #             self.log.debug(
    #                 f"Blocking from {threading.current_thread()} on {ext.thread}"
    #             )
    #         state = ext.thread_wait()
    #         if DEBUG:
    #             self.log.debug(
    #                 f"Back from wait on self {threading.current_thread()} with newstate {state}"
    #             )
    #         if state == external_state.EXITED:
    #             self._pending_threads.remove(ext)
    #             self._pending_events.append(ext.event)
