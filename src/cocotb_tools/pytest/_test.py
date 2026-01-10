# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Extend cocotb test module."""

from __future__ import annotations

from typing import Any, Callable

from cocotb._test import RunningTest
from cocotb.task import Task


class RunningTestSetup(RunningTest):
    """Running test setup without cancelling added sub-tasks."""

    def __init__(
        self, test_complete_cb: Callable[[], None], main_task: Task[None]
    ) -> None:
        """Create new instance of running test setup."""
        super().__init__(test_complete_cb=test_complete_cb, main_task=main_task)

        self.subtasks: list[Task[Any]] = []
        """Sub-tasks that must be keep alive during test setup, call and teardown."""

    def add_task(self, task: Task[Any]) -> None:
        """Add task to test setup."""
        self.subtasks.append(task)
