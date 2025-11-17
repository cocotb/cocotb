# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
from collections import deque
from functools import cached_property
from typing import Callable

from cocotb import debug
from cocotb._bridge import run_bridge_threads


class ScheduledCallback:
    __slots__ = ("_func", "_cancelled")

    def __init__(
        self,
        func: Callable[[], object],
    ) -> None:
        self._func = func
        self._cancelled: bool = False

    def _run(self) -> None:
        self._func()

    def cancel(self) -> None:
        self._cancelled = True

    def __repr__(self) -> str:
        return self._func.__name__


class EventLoop:
    def __init__(self) -> None:
        self._callbacks: deque[ScheduledCallback] = deque()
        self._cycles: int = 0

    @cached_property
    def log(self) -> logging.Logger:
        return logging.getLogger("cocotb.event_loop")

    def run(self) -> None:
        self._cycles = 0
        while self._callbacks:
            while self._callbacks:
                do_debug = debug.debug
                cb = self._callbacks.popleft()
                if not cb._cancelled:
                    if do_debug:
                        self.log.debug("Running callback %r", cb)
                    cb._run()
                elif do_debug:
                    self.log.debug("Ignoring cancelled callback %r", cb)
                if do_debug:
                    self._cycles += 1
                    if self._cycles == 100_000:
                        self.log.warning(
                            "Event loop ran 100,000 cycles without returning. An infinite loop is possible."
                        )
                        self._cycles = 0

            run_bridge_threads()

    def schedule(self, func: Callable[[], object]) -> ScheduledCallback:
        cb = ScheduledCallback(func)
        if debug.debug:
            self.log.debug("Scheduling %r", cb)
        self._callbacks.append(cb)
        return cb


_inst: EventLoop = EventLoop()
