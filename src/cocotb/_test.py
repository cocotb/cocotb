# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import functools
import inspect
from typing import Any, Callable, Coroutine, Optional, Sequence, Type, Union

from cocotb.task import Task
from cocotb.triggers import SimTimeoutError, with_timeout

_Failed: Type[BaseException]
try:
    import pytest
except ModuleNotFoundError:
    _Failed = AssertionError
else:
    try:
        with pytest.raises(Exception):
            pass
    except BaseException as _raises_e:
        _Failed = type(_raises_e)
    else:
        assert False, "pytest.raises doesn't raise an exception when it fails"


# TODO remove SimFailure once we have functionality in place to abort the test without
# having to set an exception.
class SimFailure(Exception):
    """A Test failure due to simulator failure."""


class TestTask(Task[None]):
    """
    The result of calling a :class:`cocotb.test` decorated object.

    All this class does is change ``__name__`` to show "Test" instead of "Task".

    .. versionchanged:: 1.8.0
        Moved to the ``cocotb.task`` module.
    """

    def __init__(self, inst: Coroutine[Any, Any, None], name: str) -> None:
        super().__init__(inst)
        self.name = f"Test {name}"


def _task_done_callback(task: Task[Any]) -> None:
    # if cancelled, do nothing
    if task.cancelled():
        return task.join()._react()
    # if no failure
    e = task.exception()
    if e is None:
        return task.join()._react()
    # there was a failure and no one is watching, fail test
    elif isinstance(e, (TestSuccess, AssertionError)):
        task.log.info("Test stopped by this task")
        _current_test._abort_test(e)
    else:
        task.log.error("Exception raised by this task")
        _current_test._abort_test(e)


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
            Units of ``timeout_time``, accepts any units that :class:`~cocotb.triggers.Timer` does.

        expect_fail:
            If ``True`` and the test fails a functional check via an ``assert`` statement, :func:`pytest.raises`,
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
        func: Callable[..., Coroutine[Any, Any, None]],
        name: Optional[str] = None,
        module: Optional[str] = None,
        doc: Optional[str] = None,
        timeout_time: Optional[float] = None,
        timeout_unit: str = "step",
        expect_fail: bool = False,
        expect_error: Union[Type[Exception], Sequence[Type[Exception]]] = (),
        skip: bool = False,
        stage: int = 0,
        _expect_sim_failure: bool = False,
    ) -> None:
        if timeout_time is not None:
            co = func  # must save ref because we overwrite variable "func"

            @functools.wraps(func)
            async def func(*args, **kwargs):
                running_co = Task(co(*args, **kwargs))

                try:
                    res = await with_timeout(
                        running_co, self.timeout_time, self.timeout_unit
                    )
                except SimTimeoutError:
                    running_co.cancel()
                    raise
                else:
                    return res

        self.func = func
        self.timeout_time = timeout_time
        self.timeout_unit = timeout_unit
        self.expect_fail = expect_fail
        self.expect_error: Sequence[Type[BaseException]]
        if isinstance(expect_error, type):
            self.expect_error = (expect_error,)
        else:
            self.expect_error = expect_error
        if _expect_sim_failure:
            self.expect_error = (*self.expect_error, SimFailure)
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

    # def _abort_test(self, exc: Exception) -> None:
    #     """Force this test to end early, without executing any cleanup.

    #     This happens when a background task fails, and is consistent with
    #     how the behavior has always been. In future, we may want to behave
    #     more gracefully to allow the test body to clean up.

    #     `exc` is the exception that the test should report as its reason for
    #     aborting.
    #     """
    #     if self._test_outcome is not None:  # pragma: no cover
    #         raise InternalError("Outcome already has a value, but is being set again.")
    #     self._test_outcome = Error(exc)
    #     self._test_task.kill()
