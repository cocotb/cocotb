# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import sys
from collections import deque
from typing import Callable

from cocotb import debug
from cocotb._bridge import run_bridge_threads
from cocotb._py_compat import cached_property

if sys.version_info >= (3, 10):
    from typing import ParamSpec

    P = ParamSpec("P")


class ScheduledCallback:
    __slots__ = ("_func", "_args", "_kwargs", "_cancelled")

    def __init__(
        self, func: Callable[P, object], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True


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
                cb = self._callbacks.pop()
                if not cb._cancelled:
                    if do_debug:
                        self.log.debug(
                            "Running callback %s with args=%s, kwargs=%s",
                            cb._func,
                            cb._args,
                            cb._kwargs,
                        )
                    cb._func(*cb._args, **cb._kwargs)
                elif do_debug:
                    self.log.debug(
                        "Ignoring cancelled callback %s with args=%s, kwargs=%s",
                        cb._func,
                        cb._args,
                        cb._kwargs,
                    )
                if do_debug:
                    self._cycles += 1
                    if self._cycles == 100_000:
                        self.log.warning(
                            "Event loop ran 100,000 cycles without returning. An infinite loop is possible."
                        )
                        self._cycles = 0

            run_bridge_threads()

    def schedule(
        self, func: Callable[P, object], *args: P.args, **kwargs: P.kwargs
    ) -> ScheduledCallback:
        if debug.debug:
            self.log.debug("Scheduling %s with args=%s, kwargs=%s)", func, args, kwargs)
        cb = ScheduledCallback(func, *args, **kwargs)
        self._callbacks.appendleft(cb)
        return cb


_inst: EventLoop = EventLoop()
