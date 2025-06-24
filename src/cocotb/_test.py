# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import inspect
import os
import pdb
from typing import (
    Any,
    Callable,
    Coroutine,
    List,
    Optional,
    Union,
)

import cocotb
from cocotb._deprecation import deprecated
from cocotb._exceptions import InternalError
from cocotb._outcomes import Error, Outcome, Value
from cocotb._test_functions import TestSuccess
from cocotb.task import ResultType, Task
from cocotb.triggers import NullTrigger, Trigger

_pdb_on_exception = "COCOTB_PDB_ON_EXCEPTION" in os.environ


class RunningTest:
    """State of the currently executing Test."""

    # TODO
    # Make the tasks list a TaskManager.
    # Make shutdown errors and outcome be an ExceptionGroup from that TaskManager.
    # Replace result() with passing the outcome to the done callback.
    # Make this and Task the same object which is a Coroutine.
    # Reimplement the logic in the body of an async function.
    # Make RunningTest a normal Task that the RegressionManager runs and registers a
    #  done callback with.

    def __init__(
        self, test_complete_cb: Callable[[], None], main_task: Task[None]
    ) -> None:
        self._test_complete_cb: Callable[[], None] = test_complete_cb
        self._main_task: Task[None] = main_task
        self._main_task._add_done_callback(self._test_done_callback)

        self.tasks: List[Task[Any]] = [main_task]

        self._outcome: Union[None, Outcome[None]] = None
        self._shutdown_errors: list[Outcome[None]] = []

    def _test_done_callback(self, task: Task[None]) -> None:
        self.tasks.remove(task)
        # If cancelled, end the Test without additional error. This case would only
        # occur if a child threw a CancelledError or if the Test was forced to shutdown.
        if task.cancelled():
            self.abort(Value(None))
            return
        # Handle outcome appropriately and shut down the Test.
        e = task.exception()
        if e is None:
            self.abort(Value(task.result()))
        elif isinstance(e, TestSuccess):
            task._log.info("Test stopped early by this task")
            self.abort(Value(None))
        else:
            task._log.warning(e, exc_info=e)
            self.abort(Error(e))

    def start(self) -> None:
        cocotb._scheduler_inst._schedule_task_internal(self._main_task)
        cocotb._scheduler_inst._event_loop()

    def result(self) -> Outcome[None]:
        if self._outcome is None:  # pragma: no cover
            raise InternalError("Getting result before test is completed")

        if not isinstance(self._outcome, Error) and self._shutdown_errors:
            return self._shutdown_errors[0]
        return self._outcome

    def abort(self, outcome: Outcome[None]) -> None:
        """Force this test to end early."""

        # If we are shutting down, save any errors
        if self._outcome is not None:
            if isinstance(outcome, Error):
                self._shutdown_errors.append(outcome)
            return

        # Break into pdb on test end before all Tasks are killed.
        if _pdb_on_exception and isinstance(outcome, Error):
            pdb.post_mortem(outcome.error.__traceback__)

        # Set outcome and cancel Tasks.
        self._outcome = outcome
        for task in self.tasks[:]:
            task._cancel_now()

        self._test_complete_cb()

    def add_task(self, task: Task[Any]) -> None:
        task._add_done_callback(self._task_done_callback)
        self.tasks.append(task)

    def _task_done_callback(self, task: Task[Any]) -> None:
        self.tasks.remove(task)
        # if cancelled, do nothing
        if task.cancelled():
            return
        # if there's a Task awaiting this one, don't fail
        if task.complete in cocotb._scheduler_inst._trigger2tasks:
            return
        # if no failure, do nothing
        e = task.exception()
        if e is None:
            return
        # there was a failure and no one is watching, fail test
        elif isinstance(e, TestSuccess):
            task._log.info("Test stopped early by this task")
            self.abort(Value(None))
        else:
            task._log.warning(e, exc_info=e)
            self.abort(Error(e))


def start_soon(
    coro: Union[Task[ResultType], Coroutine[Trigger, None, ResultType]],
    *,
    name: Optional[str] = None,
) -> Task[ResultType]:
    """
    Schedule a :term:`coroutine` to be run concurrently in a :class:`~cocotb.task.Task`.

    Note that this is not an :keyword:`async` function,
    and the new task will not execute until the calling task yields control.

    Args:
        coro: A :class:`!Task` or :term:`!coroutine` to be run concurrently.
        name:
            The task's name.

            .. versionadded:: 2.0

    Returns:
        The :class:`~cocotb.task.Task` that is scheduled to be run.

    .. versionadded:: 1.6
    """
    task = create_task(coro, name=name)
    cocotb._scheduler_inst._schedule_task(task)
    return task


@deprecated("Use ``cocotb.start_soon`` instead.")
async def start(
    coro: Union[Task[ResultType], Coroutine[Trigger, None, ResultType]],
    *,
    name: Optional[str] = None,
) -> Task[ResultType]:
    """
    Schedule a :term:`coroutine` to be run concurrently, then yield control to allow pending tasks to execute.

    The calling task will resume execution before control is returned to the simulator.

    When the calling task resumes, the newly scheduled task may have completed,
    raised an Exception, or be pending on a :class:`~cocotb.triggers.Trigger`.

    Args:
        coro: A :class:`!Task` or :term:`!coroutine` to be run concurrently.
        name:
            The task's name.

            .. versionadded:: 2.0

    Returns:
        The :class:`~cocotb.task.Task` that has been scheduled and allowed to execute.

    .. versionadded:: 1.6

    .. deprecated:: 2.0
        Use :func:`cocotb.start_soon` instead.
        If you need the scheduled Task to start before continuing the current Task,
        use an :class:`.Event` to block the current Task until the scheduled Task starts,
        like so:

        .. code-block:: python

            async def coro(started: Event) -> None:
                started.set()
                # Do stuff...


            task_started = Event()
            task = cocotb.start_soon(coro(task_started))
            await task_started.wait()
    """
    task = start_soon(coro, name=name)
    await NullTrigger()
    return task


def create_task(
    coro: Union[Task[ResultType], Coroutine[Trigger, None, ResultType]],
    *,
    name: Optional[str] = None,
) -> Task[ResultType]:
    """
    Construct a :term:`!coroutine` into a :class:`~cocotb.task.Task` without scheduling the task.

    The task can later be scheduled with :func:`cocotb.start` or :func:`cocotb.start_soon`.

    Args:
        coro: A :class:`!Task` or a :term:`!coroutine` to be turned into a :class:`!Task`.
        name:
            The task's name.

            .. versionadded:: 2.0

    Returns:
        Either the provided :class:`~cocotb.task.Task` or a new Task wrapping the coroutine.

    .. versionadded:: 1.6
    """
    if isinstance(coro, Task):
        if name is not None:
            coro.set_name(name)
        return coro
    elif isinstance(coro, Coroutine):
        task = Task[ResultType](coro, name=name)
        cocotb._regression_manager._running_test.add_task(task)
        return task
    elif inspect.iscoroutinefunction(coro):
        raise TypeError(
            f"Coroutine function {coro} should be called prior to being scheduled."
        )
    elif inspect.isasyncgen(coro):
        raise TypeError(
            f"{coro.__qualname__} is an async generator, not a coroutine. "
            "You likely used the yield keyword instead of await."
        )
    else:
        raise TypeError(
            f"Attempt to add an object of type {type(coro)} to the scheduler, "
            f"which isn't a coroutine: {coro!r}\n"
        )
