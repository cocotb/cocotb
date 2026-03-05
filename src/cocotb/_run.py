# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import threading
from collections.abc import Coroutine
from typing import TypeVar

import cocotb._event_loop
from cocotb.task import Task
from cocotb.triggers import Trigger

T = TypeVar("T")


def run(coro: Coroutine[Trigger, None, T]) -> T:
    """Run a coroutine using the cocotb scheduler and block until it completes, returning its result.

    .. warning::
        Can currently only be called once and cannot be used in a cocotb regression.

    Args:
        coro: The coroutine to run.

    Returns:
        The result of the coroutine.

    .. versionadded:: 2.1
    """
    e = threading.Event()
    task = Task(coro)
    task._add_done_callback(lambda _: e.set())
    task._ensure_started()
    cocotb._event_loop._inst.run()
    e.wait()
    return task.result()
