# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Extend cocotb test module."""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, Callable

from cocotb._base_triggers import Trigger
from cocotb._test_manager import TestManager
from cocotb.task import Task


class RunningTestSetup(TestManager):
    """Running test setup without cancelling added sub-tasks."""

    def __init__(
        self,
        coro: Coroutine[Trigger, None, None],
        *,
        name: str,
        test_complete_cb: Callable[[], None],
    ) -> None:
        """Create new instance of running test setup."""
        super().__init__(coro, name=name, test_complete_cb=test_complete_cb)

        self.subtasks: list[Task[Any]] = []
        """Sub-tasks that must be keep alive during test setup, call and teardown."""

    def add_task(self, task: Task[Any]) -> None:
        """Add task to test setup."""
        self.subtasks.append(task)
