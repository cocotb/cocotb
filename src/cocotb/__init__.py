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
from logging import Logger
from types import SimpleNamespace
from typing import Dict, List, Union

import cocotb.handle
import cocotb.task
import cocotb.triggers
import cocotb.types
from cocotb._bridge import bridge, resume
from cocotb._test import create_task, start, start_soon
from cocotb._test_generation import TestFactory, parametrize, test
from cocotb._version import __version__

__all__ = (
    "test",
    "parametrize",
    "TestFactory",
    "bridge",
    "resume",
    "start_soon",
    "start",
    "create_task",
    "__version__",
)


log: Logger
"""The default cocotb logger."""

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


# def start_soon(
#     coro: "Union[Task[ResultType], Coroutine[Any, Any, ResultType]]",
# ) -> "Task[ResultType]":
#     """
#     Schedule a coroutine to be run concurrently.

#     Note that this is not an ``async`` function,
#     and the new task will not execute until the calling task yields control.

#     Args:
#         coro: A task or coroutine to be run.

#     Returns:
#         The :class:`~cocotb.task.Task` that is scheduled to be run.

#     .. versionadded:: 1.6.0
#     """
#     task = create_task(coro)
#     task._schedule_resume()
#     return task


# async def start(
#     coro: "Union[Task[ResultType], Coroutine[Any, Any, ResultType]]",
# ) -> "Task[ResultType]":
#     """
#     Schedule a coroutine to be run concurrently, then yield control to allow pending tasks to execute.

#     The calling task will resume execution before control is returned to the simulator.

#     When the calling task resumes, the newly scheduled task may have completed,
#     raised an Exception, or be pending on a :class:`~cocotb.triggers.Trigger`.

#     Args:
#         coro: A task or coroutine to be run.

#     Returns:
#         The :class:`~cocotb.task.Task` that has been scheduled and allowed to execute.

#     .. versionadded:: 1.6.0
#     """
#     task = start_soon(coro)
#     await NullTrigger()
#     return task


# def _task_done_callback(task: Task[Any]) -> None:
#     e = task.exception()
#     # there was a failure and no one is watching, fail test
#     if isinstance(e, (TestSuccess, AssertionError)):
#         task.log.info("Test stopped by this task")
#         current_test().abort(e)
#     else:
#         task.log.error("Exception raised by this task")
#         current_test().abort(e)


# def create_task(
#     coro: "Union[Task[ResultType], Coroutine[Any, Any, ResultType]]",
# ) -> "Task[ResultType]":
#     """
#     Construct a coroutine into a :class:`~cocotb.task.Task` without scheduling the task.

#     The task can later be scheduled with :func:`cocotb.start` or :func:`cocotb.start_soon`.

#     Args:
#         coro: An existing task or a coroutine to be wrapped.

#     Returns:
#         Either the provided :class:`~cocotb.task.Task` or a new Task wrapping the coroutine.

#     .. versionadded:: 1.6.0
#     """
#     if isinstance(coro, Task):
#         return coro
#     task = Task(coro)
#     task._add_done_callback(_task_done_callback)
#     return task


# class TestTask(Task[None]):
#     """The result of calling a :class:`cocotb.test` decorated object.

#     All this class does is change ``__name__`` to show "Test" instead of "Task".
#     """

#     def __init__(self, inst: Coroutine[Any, Any, None], name: str) -> None:
#         super().__init__(inst)
#         self.name = f"Test {name}"
