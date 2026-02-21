# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Type stubs for cocotb._fast_sched Cython extension."""

from __future__ import annotations

from collections.abc import Coroutine, Generator
from typing import Any

from cocotb._fast_loop import _FastLoopDone
from cocotb.handle import SimHandleBase

class _FastTrigger:
    def __await__(self) -> Generator[_FastTrigger, None, _FastTrigger]: ...
    def __iter__(self) -> _FastTrigger: ...
    def __next__(self) -> _FastTrigger: ...

class RisingEdge(_FastTrigger):
    def __init__(self, handle: SimHandleBase) -> None: ...

class FallingEdge(_FastTrigger):
    def __init__(self, handle: SimHandleBase) -> None: ...

class ValueChange(_FastTrigger):
    def __init__(self, handle: SimHandleBase) -> None: ...

class ReadOnly(_FastTrigger): ...
class ReadWrite(_FastTrigger): ...

class _FastScheduler:
    exception: BaseException | None
    result: object
    _current_phase: str
    _pending_phase: str
    def __init__(
        self,
        coro: Coroutine[Any, None, Any],
        done_trigger: _FastLoopDone,
    ) -> None: ...
    def start(self) -> None: ...
