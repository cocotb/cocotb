# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

import logging
import sys
from collections import deque
from functools import cached_property
from typing import Callable, Deque

from cocotb._utils import DEBUG

if sys.version_info >= (3, 10):
    from typing import ParamSpec

    P = ParamSpec("P")


class ScheduledCallback:
    __slots__ = ("_func", "_args", "_kwargs", "_cancelled")

    def __init__(
        self, func: "Callable[P, object]", *args: "P.args", **kwargs: "P.kwargs"
    ) -> None:
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True


class EventLoop:
    def __init__(self) -> None:
        self._callbacks: Deque[ScheduledCallback] = deque()

    @cached_property
    def log(self) -> logging.Logger:
        return logging.getLogger("cocotb.event_loop")

    def run(self) -> None:
        while self._callbacks:
            cb = self._callbacks.pop()
            if not cb._cancelled:
                if DEBUG:
                    self.log.debug(
                        "Running callback %s with args=%s, kwargs=%s",
                        cb._func,
                        cb._args,
                        cb._kwargs,
                    )
                cb._func(*cb._args, **cb._kwargs)
            elif DEBUG:
                self.log.debug(
                    "Ignoring cancelled callback %s with args=%s, kwargs=%s",
                    cb._func,
                    cb._args,
                    cb._kwargs,
                )

    def schedule(
        self, func: "Callable[P, object]", *args: "P.args", **kwargs: "P.kwargs"
    ) -> ScheduledCallback:
        if DEBUG:
            self.log.debug("Scheduling %s with args=%s, kwargs=%s)", func, args, kwargs)
        cb = ScheduledCallback(func, *args, **kwargs)
        self._callbacks.appendleft(cb)
        return cb


_inst: EventLoop = EventLoop()
