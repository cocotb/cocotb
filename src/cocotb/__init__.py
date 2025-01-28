# Copyright (c) 2013 Potential Ventures Ltd
# Copyright (c) 2013 SolarFlare Communications Inc
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Potential Ventures Ltd,
#       SolarFlare Communications Inc nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL POTENTIAL VENTURES LTD BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import inspect
import logging as py_logging
from enum import auto
from types import SimpleNamespace
from typing import Any, Coroutine, Dict, List, Union

import cocotb._profiling
import cocotb.handle
import cocotb.task
import cocotb.triggers
from cocotb._decorators import (
    bridge,
    parametrize,
    resume,
    test,
)
from cocotb._deprecation import deprecated
from cocotb._scheduler import Scheduler
from cocotb._utils import DocEnum
from cocotb.regression import RegressionManager
from cocotb.result import TestSuccess

from ._version import __version__

__all__ = ("bridge", "resume", "test", "parametrize", "__version__")


log: py_logging.Logger
"""The default cocotb logger."""

_scheduler_inst: Scheduler
"""The global scheduler instance."""

regression_manager: RegressionManager
"""The global regression manager instance."""

argv: List[str]
"""The argument list as seen by the simulator."""

plusargs: Dict[str, Union[bool, str]]
"""A dictionary of "plusargs" handed to the simulation.

See :make:var:`COCOTB_PLUSARGS` for details.
"""

packages: SimpleNamespace
"""A :class:`python:types.SimpleNamespace` of package handles.

This will be populated with handles at test time if packages can be discovered
via the GPI.

.. versionadded:: 2.0
"""

SIM_NAME: str
"""The product information of the running simulator."""

SIM_VERSION: str
"""The version of the running simulator."""

_random_seed: int
"""
The value passed to the Python default random number generator.

See :envvar:`COCOTB_RANDOM_SEED` for details on how the value is computed.
This is guaranteed to hold a value at test time.
"""

top: cocotb.handle.SimHandleBase
r"""
A handle to the :envvar:`COCOTB_TOPLEVEL` entity/module.

This is equivalent to the :term:`DUT` parameter given to cocotb tests, so it can be used wherever that variable can be used.
It is particularly useful for extracting information about the :term:`DUT` in module-level class and function definitions;
and in parameters to :class:`.TestFactory`\ s.
"""

is_simulation: bool = False
"""``True`` if cocotb was loaded in a simulation."""


class SimPhase(DocEnum):
    """A phase of the time step."""

    NORMAL = (auto(), "In the Beginning Of Time Step or a Value Change phase.")
    READ_WRITE = (auto(), "In a ReadWrite phase.")
    READ_ONLY = (auto(), "In a ReadOnly phase.")


sim_phase: SimPhase = SimPhase.NORMAL
"""The current phase of the time step."""


def _task_done_callback(task: "cocotb.task.Task[Any]") -> None:
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
    elif isinstance(e, (TestSuccess, AssertionError)):
        task.log.info("Test stopped by this task")
        cocotb.regression_manager._abort_test(e)
    else:
        task.log.error("Exception raised by this task")
        cocotb.regression_manager._abort_test(e)


def start_soon(
    coro: "Union[cocotb.task.Task[cocotb.task.ResultType], Coroutine[Any, Any, cocotb.task.ResultType]]",
) -> "cocotb.task.Task[cocotb.task.ResultType]":
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
    coro: "Union[cocotb.task.Task[cocotb.task.ResultType], Coroutine[Any, Any, cocotb.task.ResultType]]",
) -> "cocotb.task.Task[cocotb.task.ResultType]":
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
        If you need the scheduled Task to run before continuing the current Task,
        follow the call to :func:`cocotb.start_soon` with an :class:`await NullTrigger() <cocotb.triggers.NullTrigger>`.
    """
    task = start_soon(coro)
    await cocotb.triggers.NullTrigger()
    return task


def create_task(
    coro: "Union[cocotb.task.Task[cocotb.task.ResultType], Coroutine[Any, Any, cocotb.task.ResultType]]",
) -> "cocotb.task.Task[cocotb.task.ResultType]":
    """
    Construct a coroutine into a :class:`~cocotb.task.Task` without scheduling the task.

    The task can later be scheduled with :func:`cocotb.start` or :func:`cocotb.start_soon`.

    Args:
        coro: An existing task or a coroutine to be wrapped.

    Returns:
        Either the provided :class:`~cocotb.task.Task` or a new Task wrapping the coroutine.

    .. versionadded:: 1.6
    """
    if isinstance(coro, cocotb.task.Task):
        return coro
    elif isinstance(coro, Coroutine):
        task = cocotb.task.Task[cocotb.task.ResultType](coro)
        task._add_done_callback(_task_done_callback)
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
