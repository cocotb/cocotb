import functools
import hashlib
import inspect
import random
import time
from typing import (
    Any,
    Callable,
    Coroutine,
    List,
    NoReturn,
    Optional,
    Tuple,
    Type,
    Union,
)

import cocotb
from cocotb._base_triggers import Trigger
from cocotb._deprecation import deprecated
from cocotb._exceptions import InternalError
from cocotb._outcomes import Error, Outcome, Value
from cocotb._typing import TimeUnit
from cocotb.task import ResultType, Task
from cocotb.triggers import NullTrigger, SimTimeoutError, with_timeout
from cocotb.utils import get_sim_time

Failed: Type[BaseException]
try:
    import pytest
except ModuleNotFoundError:
    Failed = AssertionError
else:
    try:
        with pytest.raises(Exception):
            pass
    except BaseException as _raises_e:
        Failed = type(_raises_e)
    else:
        assert False, "pytest.raises doesn't raise an exception when it fails"


# TODO remove SimFailure once we have functionality in place to abort the test without
# having to set an exception.
class SimFailure(BaseException):
    """A Test failure due to simulator failure."""


class TestSuccess(BaseException):
    """Implementation of :func:`pass_test`.

    Users are *not* intended to catch this exception type.
    """

    def __init__(self, msg: Union[str, None]) -> None:
        super().__init__(msg)
        self.msg = msg


class Test:
    """A cocotb test in a regression.

    Args:
        func:
            The test function object.

        name:
            The name of the test function.
            Defaults to ``func.__qualname__`` (the dotted path to the test function in the module).

        module:
            The name of the module containing the test function.
            Defaults to ``func.__module__`` (the name of the module containing the test function).

        doc:
            The docstring for the test.
            Defaults to ``func.__doc__`` (the docstring of the test function).

        timeout_time:
            Simulation time duration before the test is forced to fail with a :exc:`~cocotb.triggers.SimTimeoutError`.

        timeout_unit:
            Unit of ``timeout_time``, accepts any unit that :class:`~cocotb.triggers.Timer` does.

        expect_fail:
            If ``True`` and the test fails a functional check via an :keyword:`assert` statement, :func:`pytest.raises`,
            :func:`pytest.warns`, or :func:`pytest.deprecated_call`, the test is considered to have passed.
            If ``True`` and the test passes successfully, the test is considered to have failed.

        expect_error:
            Mark the result as a pass only if one of the given exception types is raised in the test.

        skip:
            Don't execute this test as part of the regression.
            The test can still be run manually by setting :envvar:`COCOTB_TESTCASE`.

        stage:
            Order tests logically into stages.
            Tests from earlier stages are run before tests from later stages.
    """

    def __init__(
        self,
        *,
        func: Callable[..., Coroutine[Trigger, None, None]],
        name: Optional[str] = None,
        module: Optional[str] = None,
        doc: Optional[str] = None,
        timeout_time: Optional[float] = None,
        timeout_unit: TimeUnit = "step",
        expect_fail: bool = False,
        expect_error: Union[Type[BaseException], Tuple[Type[BaseException], ...]] = (),
        skip: bool = False,
        stage: int = 0,
        _expect_sim_failure: bool = False,
    ) -> None:
        self.func: Callable[..., Coroutine[Trigger, None, None]]
        if timeout_time is not None:
            co = func  # must save ref because we overwrite variable "func"

            @functools.wraps(func)
            async def f(*args: object, **kwargs: object) -> None:
                running_co = Task(co(*args, **kwargs))

                try:
                    await with_timeout(running_co, timeout_time, timeout_unit)
                except SimTimeoutError:
                    running_co.cancel()
                    raise

            self.func = f
        else:
            self.func = func
        self.timeout_time = timeout_time
        self.timeout_unit = timeout_unit
        self.expect_fail = expect_fail
        if isinstance(expect_error, type):
            expect_error = (expect_error,)
        if _expect_sim_failure:
            expect_error += (SimFailure,)
        self.expect_error = expect_error
        self._expect_sim_failure = _expect_sim_failure
        self.skip = skip
        self.stage = stage
        self.name = self.func.__qualname__ if name is None else name
        self.module = self.func.__module__ if module is None else module
        self.doc = self.func.__doc__ if doc is None else doc
        if self.doc is not None:
            # cleanup docstring using `trim` function from PEP257
            self.doc = inspect.cleandoc(self.doc)
        self.fullname = f"{self.module}.{self.name}"

        self.tasks: List[Task[Any]] = []

        self._test_complete_cb: Callable[[], None]
        self._main_task: Task[None]
        self._outcome: Union[None, Outcome[Any]] = None
        self._shutdown_errors: list[Outcome[Any]] = []
        self._started: bool = False
        self._start_time: float
        self._start_sim_time: float

    def init(self, _test_complete_cb: Callable[[], None]) -> None:
        self._test_complete_cb = _test_complete_cb
        self._main_task = TestTask(self.func(cocotb.top), self.name)
        self._main_task._add_done_callback(self._test_done_callback)
        self.tasks.append(self._main_task)

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
            self.abort(Value(e))
        else:
            task._log.warning(e, exc_info=e)
            self.abort(Error(e))

    def start(self) -> None:
        # seed random number generator based on test module, name, and COCOTB_RANDOM_SEED
        hasher = hashlib.sha1()
        hasher.update(self.fullname.encode())
        seed = cocotb.RANDOM_SEED + int(hasher.hexdigest(), 16)
        random.seed(seed)

        self._start_sim_time = get_sim_time("ns")
        self._start_time = time.time()

        self._started = True

        cocotb._scheduler_inst._schedule_task_internal(self._main_task)
        cocotb._scheduler_inst._event_loop()

    def result(self) -> Outcome[Any]:
        if self._outcome is None:  # pragma: no cover
            raise InternalError("Getting result before test is completed")

        if not isinstance(self._outcome, Error) and self._shutdown_errors:
            return self._shutdown_errors[0]
        return self._outcome

    def abort(self, outcome: Outcome[Any]) -> None:
        """Force this test to end early."""

        # If we are shutting down, save any errors
        if self._outcome is not None:
            if isinstance(outcome, Error):
                self._shutdown_errors.append(outcome)
            return

        # Set outcome and cancel Tasks.
        self._outcome = outcome
        for task in self.tasks[:]:
            task._cancel_now()

        if self._started:
            self.wall_time = time.time() - self._start_time
            self.sim_time_ns = get_sim_time("ns") - self._start_sim_time
        else:
            self.wall_time = 0
            self.sim_time_ns = 0
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
            self.abort(Value(e))
        else:
            task._log.warning(e, exc_info=e)
            self.abort(Error(e))


class TestTask(Task[None]):
    """Specialized Task for Tests."""

    def __init__(self, inst: Coroutine[Trigger, None, None], name: str) -> None:
        super().__init__(inst)
        self._name = f"Test {name}"


def start_soon(
    coro: Union[Task[ResultType], Coroutine[Any, Any, ResultType]],
) -> Task[ResultType]:
    """
    Schedule a coroutine to be run concurrently in a :class:`~cocotb.task.Task`.

    Note that this is not an :keyword:`async` function,
    and the new task will not execute until the calling task yields control.

    Args:
        coro: A task or coroutine to be run.

    Returns:
        The :class:`~cocotb.task.Task` that is scheduled to be run.

    .. versionadded:: 1.6
    """
    task = create_task(coro)
    cocotb._scheduler_inst._schedule_task(task)
    return task


@deprecated("Use ``cocotb.start_soon`` instead.")
async def start(
    coro: Union[Task[ResultType], Coroutine[Any, Any, ResultType]],
) -> Task[ResultType]:
    """
    Schedule a coroutine to be run concurrently, then yield control to allow pending tasks to execute.

    The calling task will resume execution before control is returned to the simulator.

    When the calling task resumes, the newly scheduled task may have completed,
    raised an Exception, or be pending on a :class:`~cocotb.triggers.Trigger`.

    Args:
        coro: A task or coroutine to be run.

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
    task = start_soon(coro)
    await NullTrigger()
    return task


def create_task(
    coro: Union[Task[ResultType], Coroutine[Any, Any, ResultType]],
) -> Task[ResultType]:
    """
    Construct a coroutine into a :class:`~cocotb.task.Task` without scheduling the task.

    The task can later be scheduled with :func:`cocotb.start` or :func:`cocotb.start_soon`.

    Args:
        coro: An existing task or a coroutine to be wrapped.

    Returns:
        Either the provided :class:`~cocotb.task.Task` or a new Task wrapping the coroutine.

    .. versionadded:: 1.6
    """
    if isinstance(coro, Task):
        return coro
    elif isinstance(coro, Coroutine):
        task = Task[ResultType](coro)
        cocotb._regression_manager._test.add_task(task)
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


def pass_test(msg: Union[str, None] = None) -> NoReturn:
    """Force a test to pass.

    The test will end and enter termination phase when this is called.

    Args:
        msg: The message to display when the test passes.
    """
    raise TestSuccess(msg)
