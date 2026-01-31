# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pdb
import sys
from collections.abc import Coroutine
from typing import (
    Any,
    Callable,
    NoReturn,
)

import cocotb
import cocotb._event_loop
from cocotb._base_triggers import Event, NullTrigger, Trigger
from cocotb._deprecation import deprecated
from cocotb.task import ResultType, Task
from cocotb_tools import _env

if sys.version_info < (3, 11):
    from exceptiongroup import BaseExceptionGroup

_pdb_on_exception = _env.as_bool("COCOTB_PDB_ON_EXCEPTION")


class TestManager:
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
        self,
        test_coro: Coroutine[Trigger, None, Any],
        *,
        name: str,
        test_complete_cb: Callable[[], None],
    ) -> None:
        self._test_complete_cb: Callable[[], None] = test_complete_cb

        # We create the main task here so that the init checks can be done immediately.
        self._main_task = Task[None](test_coro, name=f"Test {name}")
        self._tasks: list[Task[Any]] = []
        self._excs: list[BaseException] = []
        self._finishing: bool = False
        self._complete: bool = False
        self._done = Event()

    def _test_done_callback(self, task: Task[None]) -> None:
        self.remove_task(task)
        # If cancelled, end the Test without additional error. This case would only
        # occur if a child threw a CancelledError or if the Test was forced to shutdown.
        if task.cancelled():
            self.abort()
            return
        # Handle outcome appropriately and shut down the Test.
        e = task.exception()
        if e is None:
            self.abort()
        elif isinstance(e, TestSuccess):
            task._log.info("Test stopped early by this task")
            self.abort()
        else:
            self.abort(e)

    def start(self) -> None:
        # set global current test manager
        global _current_test
        _current_test = self

        # start main task
        self._main_task._add_done_callback(self._test_done_callback)
        self._main_task._ensure_started()
        self._tasks.append(self._main_task)

        cocotb._event_loop._inst.run()

    def exception(self) -> BaseException | None:
        if self._excs:
            if len(self._excs) == 1:
                return self._excs[0]
            else:
                return BaseExceptionGroup("Multiple exceptions in test", self._excs)
        return None

    def result(self) -> None:
        exc = self.exception()
        if exc:
            raise exc

    def done(self) -> bool:
        """Return whether the test has completed."""
        return self._complete

    def abort(self, exc: BaseException | None = None) -> None:
        """Force this test to end early."""

        if exc is not None:
            self._excs.append(exc)

        if self._finishing:
            return
        self._finishing = True

        # Break into pdb on test end before all Tasks are killed.
        if _pdb_on_exception and exc is not None:
            try:
                pdb.post_mortem(exc.__traceback__)
            except BaseException:
                pdb.set_trace()

        # Cancel Tasks.
        for task in self._tasks[:]:
            task._cancel_now()

        # Register function to clean up global state once all Tasks have ended.
        if self._done.is_set():
            self._on_complete()
        else:
            self._done.wait()._register(self._on_complete)

    def _on_complete(self) -> None:
        # Clear the current global current test manager
        global _current_test
        _current_test = None

        self._complete = True

        # Tell RegressionManager the test is complete
        self._test_complete_cb()

    def add_task(self, task: Task[Any]) -> None:
        task._add_done_callback(self._task_done_callback)
        self._tasks.append(task)
        self._done.clear()

    def remove_task(self, task: Task[Any]) -> None:
        self._tasks.remove(task)
        if not self._tasks:
            self._done.set()

    def _task_done_callback(self, task: Task[Any]) -> None:
        self.remove_task(task)
        # if cancelled, do nothing
        if task.cancelled():
            return
        # if there's a Task awaiting this one, don't fail
        if task.complete._callbacks:
            return
        # if no failure, do nothing
        e = task.exception()
        if e is None:
            return
        # there was a failure and no one is watching, fail test
        elif isinstance(e, TestSuccess):
            task._log.info("Test stopped early by this task")
            self.abort()
        else:
            self.abort(e)


def start_soon(
    coro: Task[ResultType] | Coroutine[Trigger, None, ResultType],
    *,
    name: str | None = None,
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
    task._ensure_started()
    return task


@deprecated("Use ``cocotb.start_soon`` instead.")
async def start(
    coro: Task[ResultType] | Coroutine[Trigger, None, ResultType],
    *,
    name: str | None = None,
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
    coro: Task[ResultType] | Coroutine[Trigger, None, ResultType],
    *,
    name: str | None = None,
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
    if _current_test is None:
        raise RuntimeError("No test is currently running; cannot schedule new Task.")

    if isinstance(coro, Task):
        # We do not add the done callback here, so that custom Tasks are not considered
        # "toplevel" tasks and end the test when they fail.
        if name is not None:
            coro.set_name(name)
        return coro

    task = Task[ResultType](coro, name=name)
    _current_test.add_task(task)

    return task


class TestSuccess(BaseException):
    """Implementation of :func:`pass_test`.

    Users are *not* intended to catch this exception type.
    """

    def __init__(self, msg: str | None) -> None:
        super().__init__(msg)
        self.msg = msg


def pass_test(msg: str | None = None) -> NoReturn:
    """Force a test to pass.

    The test will end and enter termination phase when this is called.

    Args:
        msg: The message to display when the test passes.
    """
    raise TestSuccess(msg)


_current_test: TestManager | None = None
"""The currently executing test's state."""
