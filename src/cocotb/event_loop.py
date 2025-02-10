# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import logging
import os
from typing import Any, Callable, List

# Sadly the Python standard logging module is very slow so it's better not to
# make any calls by testing a boolean flag first
_debug = "COCOTB_SCHEDULER_DEBUG" in os.environ


class CallbackHandle:
    def __init__(self, func: Callable[..., Any], args: Any) -> None:
        self._func = func
        self._args = args
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def _run(self) -> None:
        self._func(*self._args)


class EventLoop:
    def __init__(self) -> None:
        self._log = logging.getLogger("cocotb.scheduler")
        if _debug:
            self._log.setLevel(logging.DEBUG)
        self._scheduled_tasks: List[CallbackHandle] = []

    def run(self) -> None:
        """Run the main event loop."""
        while self._scheduled_tasks:
            handle = self._scheduled_tasks.pop(0)
            if not handle._cancelled:
                handle._run()

    def schedule(self, func: Callable[..., Any], *args: Any) -> CallbackHandle:
        """Schedule a function to run."""
        self._log.info(f"Scheduling {func}{args!r}")
        # breakpoint()
        handle = CallbackHandle(func, args)
        self._scheduled_tasks.append(handle)
        return handle


_instance = EventLoop()
"""The global scheduler instance."""
# TODO Make this not a global singleton by passing it around Triggers and Tasks.
