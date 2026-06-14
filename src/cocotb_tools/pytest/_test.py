# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Custom test manager extensions for cocotb tests running in pytest."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, Callable

from cocotb._base_triggers import Trigger
from cocotb._test_manager import TestManager
from cocotb.task import Task


class RunningTestSetup(TestManager):
    """A test manager for running the setup phase without canceling sub-tasks.

    This class extends cocotb's :class:`~cocotb._test_manager.TestManager` to allow
    sub-tasks spawned during fixture setup to survive beyond the setup phase and remain active
    throughout the test call and teardown phases.
    """

    def __init__(
        self,
        coro: Coroutine[Trigger, None, None],
        *,
        name: str,
        test_complete_cb: Callable[[], None],
    ) -> None:
        """Initialize a new RunningTestSetup instance.

        Args:
            coro: The setup coroutine to execute.
            name: A descriptive name for the setup task.
            test_complete_cb: Callback executed when the setup task completes.
        """
        super().__init__(coro, name=name, test_complete_cb=test_complete_cb)

        self.subtasks: list[Task[Any]] = []
        """Sub-tasks that must be kept alive during test setup, call, and teardown."""

    def add_task(self, task: Task[Any]) -> None:
        """Add a sub-task to be tracked and preserved across test phases.

        Args:
            task: The cocotb Task to preserve.
        """
        self.subtasks.append(task)
