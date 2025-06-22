# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import functools
import logging
import os
import threading
from enum import IntEnum
from typing import (
    Callable,
    Coroutine,
    Generic,
    TypeVar,
    Union,
)

import cocotb
from cocotb._base_triggers import Event, Trigger
from cocotb._exceptions import InternalError
from cocotb._outcomes import Outcome
from cocotb._py_compat import ParamSpec

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ

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
            if _debug:
                self._log.debug(
                    f"Changing state from {self.state} -> {new_state} from {threading.current_thread()}"
                )
            self.state = new_state
            self.cond.notify()

    def thread_done(self) -> None:
        if _debug:
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

            if self.state == external_state.INIT:
                raise Exception(
                    f"Thread {self.thread} state was not allowed from {threading.current_thread()}"
                )

        return self.state
