# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import collections.abc
import inspect
import logging
import traceback
from types import CoroutineType
import warnings
from asyncio import CancelledError, InvalidStateError
from enum import auto
from typing import (
    Any,
    Callable,
    Coroutine,
    Generator,
    Generic,
    List,
    Optional,
    Set,
    TypeVar,
    Union,
    cast,
)

import cocotb
import cocotb.triggers
import cocotb._scheduler
from cocotb._outcomes import Error, Outcome, Value
from cocotb._py_compat import cached_property
from cocotb._utils import DocEnum, extract_coro_stack, remove_traceback_frames

#: Task result type
ResultType = TypeVar("ResultType")


class TaskState(DocEnum):
    """State of a Task."""

    UNSTARTED = (auto(), "Task created, but never run and not scheduled")
    SCHEDULED = (auto(), "Task in Scheduler queue to run soon")
    PENDING = (auto(), "Task waiting for Trigger to fire")
    RUNNING = (auto(), "Task is currently running")
    FINISHED = (auto(), "Task has finished with a value or Exception")
    CANCELLED = (auto(), "Task was cancelled before it finished")
    CANCELLING = (auto(), "Task cancellation is scheduled")


class Task(Generic[ResultType]):
    """Concurrently executing task.

    This class is not intended for users to directly instantiate.
    Use :func:`cocotb.create_task` to create a Task object,
    or use :func:`cocotb.start_soon` or :func:`cocotb.start` to
    create a Task and schedule it to run.

    .. versionchanged:: 1.8.0
        Moved to the ``cocotb.task`` module.

    .. versionchanged:: 2.0
        The ``retval``, ``_finished``, and ``__bool__`` methods were removed.
        Use :meth:`result`, :meth:`done`, and :meth:`done` methods instead, respectively.
    """

    _id_count = 0  # used by the scheduler for debug

    def __init__(self, inst: CoroutineType) -> None:
        self._native_coroutine = False
        if inspect.iscoroutinefunction(inst):
            raise TypeError(
                f"Coroutine function {inst} should be called prior to being "
                "scheduled."
            )
        elif inspect.isasyncgen(inst):
            raise TypeError(
                f"{inst.__qualname__} is an async generator, not a coroutine. "
                "You likely used the yield keyword instead of await."
            )
        elif inspect.iscoroutine(inst):
            self._native_coroutine = True
        elif not isinstance(inst, collections.abc.Coroutine):
            raise TypeError(f"{inst} isn't a valid coroutine!")

        self._coro: Coroutine[cocotb.triggers.Trigger, None, Any] = inst
        self._state: TaskState = TaskState.UNSTARTED
        self._outcome: Union[Outcome[ResultType], None] = None
        self._callback_handle: Union[cocotb.triggers._CallbackHandle, cocotb._scheduler.CallbackHandle, None] = None
        self._cancelled_error: Union[CancelledError, None] = None
        self._done_callbacks: List[Callable[[Task[Any]], Any]] = []

        self._task_id = self._id_count
        type(self)._id_count += 1
        _all_tasks.add(self)

        self.name = f"Task {self._task_id}"

    @cached_property
    def log(self) -> logging.Logger:
        # Creating a logger is expensive, only do it if we actually plan to
        # log anything
        return logging.getLogger(
            f"cocotb.{self.name}.{self._coro.__qualname__}"
        )

    def _get_coro_stack(self) -> traceback.StackSummary:
        """Get the coroutine callstack of this Task."""

        if not self._native_coroutine:
            raise TypeError(f"Can't get stack of object of type {type(self._coro).__qualname__}")

        coro_stack = extract_coro_stack(cast(CoroutineType, self._coro))

        # Remove Trigger.__await__() from the stack, as it's not really useful
        if len(coro_stack) > 0 and coro_stack[-1].name == "__await__":
            coro_stack.pop()

        return coro_stack

    def __repr__(self) -> str:
        if self._native_coroutine:
            coro_stack = self._get_coro_stack()
            try:
                coro_name = coro_stack[-1].name
            # coro_stack may be empty if:
            # - exhausted generator
            # - finished coroutine
            except IndexError:
                try:
                    coro_name = self._coro.__name__
                except AttributeError:
                    coro_name = type(self._coro).__name__

        if self._state is TaskState.RUNNING:
            fmt = "<{name} running coro={coro}()>"
        elif self._state is TaskState.FINISHED:
            fmt = "<{name} finished coro={coro}() outcome={outcome}>"
        elif self._state is TaskState.PENDING:
            fmt = "<{name} pending coro={coro}() trigger={trigger}>"
        elif self._state is TaskState.SCHEDULED:
            fmt = "<{name} scheduled coro={coro}()>"
        elif self._state is TaskState.UNSTARTED:
            fmt = "<{name} created coro={coro}()>"
        elif self._state is TaskState.CANCELLED:
            fmt = (
                "<{name} cancelled coro={coro} with={cancelled_error} outcome={outcome}"
            )
        else:
            raise RuntimeError("Task in unknown state")

        # TODO fix this
        repr_string = fmt.format(
            name=self.name,
            coro=coro_name,
            trigger=self._trigger,
            outcome=self._outcome,
            cancelled_error=self._cancelled_error,
        )
        return repr_string

    # def _advance(self) -> None:
    #     """Advance to the next yield in this coroutine.

    #     Args:
    #         outcome: The :any:`outcomes.Outcome` object to resume with.

    #     Returns:
    #         The object yielded from the coroutine or None if coroutine finished

    #     """
    #     try:
    #         self._state = TaskState.RUNNING
    #         trigger = self._coro.send(None)
    #     except StopIteration as e:
    #         self._outcome = Value(e.value)
    #         self._state = TaskState.FINISHED
    #     except BaseException as e:
    #         self._outcome = Error(remove_traceback_frames(e, ["_advance", "send"]))
    #         self._state = TaskState.FINISHED
    #     else:
    #         # register scheduling this task to continue
    #         handle = trigger._register()

    #     if self.done():
    #         self._cleanup()

    def _cleanup(self) -> None:
        # Close coroutine so there is no RuntimeWarning that it was never awaited
        self._coro.close()

        for callback in self._done_callbacks:
            callback(self)

    # @deprecated(
    #     "Using `task` directly is prefered to `task.join()` in all situations where the latter could be used.`"
    # )
    # def join(self) -> "cocotb.triggers._Join[ResultType]":
    #     """Wait for the task to complete.

    #     Returns:
    #         A :class:`~cocotb.triggers.Join` trigger which, if awaited, will block until the given Task completes.

    #     .. code-block:: python3

    #         my_task = cocotb.start_soon(my_coro())
    #         await my_task.join()
    #         # "my_task" is done here

    #     .. deprecated:: 2.0

    #         Using ``task`` directly is prefered to ``task.join()`` in all situations where the latter could be used.
    #     """

    @cached_property
    def _join(self) -> cocotb.triggers.Trigger:
        return cocotb.triggers._Join(self)

    def cancel(self, msg: Optional[str] = None) -> None:
        """Cancel a Task's further execution.

        When a Task is cancelled, a :exc:`asyncio.CancelledError` is thrown into the Task.
        """
        # TODO check state, set cancellation, schedule cancellation
        if self._state in (TaskState.FINISHED, TaskState.CANCELLED, TaskState.CANCELLING):
            return
        # UNSTARTED, SCHEDULED, PENDING, RUNNING

        self._cancelled_error = CancelledError(msg)

        if self._state is TaskState.UNSTARTED:
            # must fail immediately
            self._state = TaskState.CANCELLED
            self._cleanup()
        elif self._state is TaskState.PENDING:
            self._callback_handle.cancel()
            self._schedule_resume()
        elif
        self._state is TaskState.CANCELLING



    def cancelling(self) -> bool:
        return self._state is TaskState.CANCELLING

    def cancelled(self) -> bool:
        """Return ``True`` if the Task was cancelled."""
        return self._state is TaskState.CANCELLED

    def done(self) -> bool:
        """Return ``True`` if the Task has finished executing."""
        return self._state in (TaskState.FINISHED, TaskState.CANCELLED)

    def result(self) -> ResultType:
        """Return the result of the Task.

        If the Task ran to completion, the result is returned.
        If the Task failed with an exception, the exception is re-raised.
        If the Task was cancelled, the CancelledError is re-raised.
        If the coroutine is not yet complete, a :exc:`asyncio.InvalidStateError` is raised.
        """
        if self._state is TaskState.CANCELLED:
            raise self._cancelled_error
        elif self._state is TaskState.FINISHED:
            return self._outcome.get()
        else:
            raise InvalidStateError("result is not yet available")

    def exception(self) -> Optional[BaseException]:
        """Return the exception of the Task.

        If the Task ran to completion, ``None`` is returned.
        If the Task failed with an exception, the exception is returned.
        If the Task was cancelled, the CancelledError is re-raised.
        If the coroutine is not yet complete, a :exc:`asyncio.InvalidStateError` is raised.
        """
        if self._state is TaskState.CANCELLED:
            raise self._cancelled_error
        elif self._state is TaskState.FINISHED:
            if isinstance(self._outcome, Error):
                return self._outcome.error
            else:
                return None
        else:
            raise InvalidStateError("result is not yet available")

    def _add_done_callback(self, callback: Callable[["Task[ResultType]"], Any]) -> None:
        """Add *callback* to the list of callbacks to be run once the Task becomes "done".

        Args:
            callback: The callback to run once "done".

        .. note::
            If the task is already done, calling this function will call the callback immediately.
        """
        if self.done():
            callback(self)
        self._done_callbacks.append(callback)

    def __await__(self) -> Generator[Any, Any, ResultType]:
        # TODO this needs to ensure that the task is running
        yield self._join
        return self.result()


_all_tasks: Set[Task[Any]] = set()
_current_task: Union[Task[Any], None] = None


def all_tasks() -> Set[Task[Any]]:
    return _all_tasks


def current_task() -> Union[Task[Any], None]:
    return _current_task

    # if task.done():
    #     if _debug:
    #         self.log.debug(f"{task} completed with {task._outcome}")
    #     assert result is None
    #     self._unschedule(task)

    # # Don't handle the result if we're shutting down
    # if self._terminate:
    #     return

    # if not task.done():
    #     if _debug:
    #         self.log.debug(f"{task!r} yielded {result} ({cocotb.sim_phase})")
    #     try:
    #         result = self._trigger_from_any(result)
    #     except TypeError as exc:
    #         # restart this task with an exception object telling it that
    #         # it wasn't allowed to yield that
    #         self._schedule_task(task, _outcomes.Error(exc))
    #     else:
    #         self._schedule_task_upon(task, result)

    # def _react(self, trigger: Trigger) -> None:
    #     """Called when a :class:`~cocotb.triggers.Trigger` fires.

    #     Finds all Tasks waiting on the Trigger that fired and queues them.
    #     """
    #     if _debug:
    #         self.log.debug(f"Trigger fired: {trigger}")

    #     # find all tasks waiting on trigger that fired
    #     try:
    #         scheduling = self._trigger2tasks.pop(trigger)
    #     except KeyError:
    #         # GPI triggers should only be ever pending if there is an
    #         # associated task waiting on that trigger, otherwise it would
    #         # have been unprimed already
    #         if isinstance(trigger, GPITrigger):
    #             self.log.critical(f"No tasks waiting on trigger that fired: {trigger}")
    #             trigger.log.info("I'm the culprit")
    #         # For Python triggers this isn't actually an error - we might do
    #         # event.set() without knowing whether any tasks are actually
    #         # waiting on this event, for example
    #         elif _debug:
    #             self.log.debug(f"No tasks waiting on trigger that fired: {trigger}")
    #         return

    #     if _debug:
    #         debugstr = "\n\t".join([str(task) for task in scheduling])
    #         if len(scheduling) > 0:
    #             debugstr = "\n\t" + debugstr
    #         self.log.debug(
    #             f"{len(scheduling)} pending tasks for trigger {trigger}{debugstr}"
    #         )

    #     # queue all tasks to wake up
    #     for task in scheduling:
    #         # unset trigger
    #         task._trigger = None
    #         self._schedule_task(task)

    #     # cleanup trigger
    #     trigger._cleanup()

    # def _schedule_task_upon(self, task: Task[Any], trigger: Trigger) -> None:
    #     """Schedule `task` to be resumed when `trigger` fires."""
    #     # TODO Move this all into Task
    #     task._trigger = trigger
    #     TaskState = TaskState.PENDING

    #     trigger_tasks = self._trigger2tasks.setdefault(trigger, [])
    #     trigger_tasks.append(task)

    #     if not trigger._primed:
    #         if trigger_tasks != [task]:
    #             # should never happen
    #             raise InternalError("More than one task waiting on an unprimed trigger")

    #         try:
    #             # TODO maybe associate the react method with the trigger object so
    #             # we don't have to do a type check here.
    #             if isinstance(trigger, GPITrigger):
    #                 trigger._prime(self._sim_react)
    #             else:
    #                 trigger._prime(self._react)
    #         except Exception as e:
    #             # discard the trigger we associated, it will never fire
    #             self._trigger2tasks.pop(trigger)

    #             # replace it with a new trigger that throws back the exception
    #             self._schedule_task(task, outcome=_outcomes.Error(e))


    # def _schedule_task(
    #     self, task: Task[Any], outcome: _outcomes.Outcome[Any] = _none_outcome
    # ) -> None:
    #     """Queue *task* for scheduling.

    #     It is an error to attempt to queue a task that has already been queued.
    #     """
    #     # Don't queue the same task more than once (gh-2503)
    #     if task in self._scheduled_tasks:
    #         raise InternalError("Task was queued more than once.")
    #     # TODO Move state tracking into Task
    #     TaskState = TaskState.SCHEDULED
    #     self._scheduled_tasks[task] = outcome


    # def _resume_task(self, task: Task, outcome: _outcomes.Outcome[Any]) -> None:
    #     """Resume *task* with *outcome*.

    #     Args:
    #         task: The task to schedule.
    #         outcome: The outcome to inject into the *task*.

    #     Scheduling runs *task* until it either finishes or reaches the next ``await`` statement.
    #     If *task* completes, it is unscheduled, a Join trigger fires, and test completion is inspected.
    #     Otherwise, it reached an ``await`` and we have a result object which is converted to a trigger,
    #     that trigger is primed,
    #     then that trigger and the *task* are registered with the :attr:`_trigger2tasks` map.
    #     """
    #     if self._current_task is not None:
    #         raise InternalError("_schedule() called while another Task is executing")
    #     try:
    #         self._current_task = task

    #         result = task._advance(outcome=outcome)

    #         # We do not return from here until pending threads have completed, but only
    #         # from the main thread, this seems like it could be problematic in cases
    #         # where a sim might change what this thread is.

    #         if self._main_thread is threading.current_thread():
    #             for ext in self._pending_threads:
    #                 ext.thread_start()
    #                 if _debug:
    #                     self.log.debug(
    #                         f"Blocking from {threading.current_thread()} on {ext.thread}"
    #                     )
    #                 state = ext.thread_wait()
    #                 if _debug:
    #                     self.log.debug(
    #                         f"Back from wait on self {threading.current_thread()} with newstate {state}"
    #                     )
    #                 if state == external_state.EXITED:
    #                     self._pending_threads.remove(ext)
    #                     self._pending_events.append(ext.event)
    #     finally:
    #         self._current_task = None
