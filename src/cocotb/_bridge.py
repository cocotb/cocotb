# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import functools
import logging
import threading
from bdb import BdbQuit
from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Generic,
    List,
    TypeVar,
    Union,
)

import cocotb
from cocotb import debug
from cocotb._base_triggers import Event, Trigger
from cocotb._exceptions import InternalError
from cocotb._outcomes import Error, Value, capture
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
        return queue_function(func(*args, **kwargs))

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
        return run_in_executor(func, *args, **kwargs)

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


pending_threads: List[external_waiter[Any]] = []


def queue_function(task: Coroutine[Trigger, None, Result]) -> Result:
    """Queue *task* for execution and switch back to main thread."""
    # We should be able to find ourselves inside the _pending_threads list
    matching_threads = [
        t for t in pending_threads if t.thread == threading.current_thread()
    ]
    if len(matching_threads) == 0:
        raise RuntimeError("queue_function called from unrecognized thread")

    # Raises if there is more than one match. This can never happen, since
    # each entry always has a unique thread.
    (t,) = matching_threads

    outcome: Union[Outcome[Result], None] = None

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
    # must register this with test as there's no way to clean up with threading
    cocotb.start_soon(wrapper())
    # The scheduler thread blocks in `thread_wait`, and is woken when we
    # call `thread_suspend` - so we need to make sure the task is
    # queued before that.
    t.thread_suspend()
    # This blocks the calling `@external` thread until the task finishes
    event.wait()
    assert outcome is not None
    return outcome.get()


def run_in_executor(
    func: "Callable[P, Result]", *args: "P.args", **kwargs: "P.kwargs"
) -> Coroutine[Trigger, None, Result]:
    """Run the task in a separate execution thread and return an awaitable object for the caller."""
    # Create a thread
    # Create a trigger that is called as a result of the thread finishing
    # Create an Event object that the caller can await on
    # Event object set when the thread finishes execution, this blocks the
    # calling task (but not the thread) until the external completes

    waiter = external_waiter[Result]()

    def execute_external() -> None:
        waiter._outcome = capture(func, *args, **kwargs)
        waiter.thread_done()

    async def wrapper() -> Result:
        thread = threading.Thread(
            group=None,
            target=execute_external,
            name=func.__qualname__ + "_thread",
        )

        waiter.thread = thread
        pending_threads.append(waiter)

        await waiter.event.wait()

        return waiter.result  # raises if there was an exception

    return wrapper()


def run_bridge_threads() -> None:
    """Progresses the state of all pending threads."""
    # TODO Incorporate all this into a Task-like class which does the following as part
    # of its resume() so we don't have to call this function as part of the main event
    # loop.

    # We do not return from here until pending threads have completed, but only
    # from the main thread, this seems like it could be problematic in cases
    # where a sim might change what this thread is.

    for ext in pending_threads:
        ext.thread_start()
        if debug.debug:
            ext._log.debug(
                "Blocking from %s on %s",
                threading.current_thread(),
                ext.thread,
            )
        state = ext.thread_wait()
        if debug.debug:
            ext._log.debug(
                "Back from wait on self %s with newstate %s",
                threading.current_thread(),
                state,
            )
        if state == external_state.EXITED:
            pending_threads.remove(ext)
            ext.event.set()
