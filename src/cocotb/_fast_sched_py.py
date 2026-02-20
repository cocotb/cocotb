# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Pure-Python fallback for the fast mini-scheduler.

Provides the same API as :mod:`cocotb._fast_sched` (Cython) so that the
fast async/await loop works even when the Cython extension is not compiled.
Slower than the Cython version but still significantly faster than the
standard cocotb Task/EventLoop/Trigger path.
"""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any

from cocotb import simulator
from cocotb._fast_loop import _FastLoopDone

# ---------------------------------------------------------------------------
# GPI edge-type constants
# ---------------------------------------------------------------------------
_RISING: int = simulator.RISING
_FALLING: int = simulator.FALLING
_VALUE_CHANGE: int = simulator.VALUE_CHANGE


# ---------------------------------------------------------------------------
# Fast trigger base — zero-allocation __await__ protocol
# ---------------------------------------------------------------------------


class _FastTrigger:
    """Base for fast triggers.

    The trigger object acts as its own iterator, yielding itself exactly
    once per ``await``.  No intermediate objects are allocated.
    """

    __slots__ = ("_iter_started",)

    def __await__(self) -> _FastTrigger:
        self._iter_started = False
        return self

    def __iter__(self) -> _FastTrigger:
        return self

    def __next__(self) -> _FastTrigger:
        if self._iter_started:
            raise StopIteration(self)
        self._iter_started = True
        return self


# ---------------------------------------------------------------------------
# Concrete trigger types
# ---------------------------------------------------------------------------


class RisingEdge(_FastTrigger):
    """Fast trigger: fires on the rising edge of a signal."""

    __slots__ = ("_sim_hdl",)

    def __init__(self, handle: object) -> None:
        self._sim_hdl: simulator.sim_obj = handle._handle  # type: ignore[attr-defined]


class FallingEdge(_FastTrigger):
    """Fast trigger: fires on the falling edge of a signal."""

    __slots__ = ("_sim_hdl",)

    def __init__(self, handle: object) -> None:
        self._sim_hdl: simulator.sim_obj = handle._handle  # type: ignore[attr-defined]


class ValueChange(_FastTrigger):
    """Fast trigger: fires on any value change of a signal."""

    __slots__ = ("_sim_hdl",)

    def __init__(self, handle: object) -> None:
        self._sim_hdl: simulator.sim_obj = handle._handle  # type: ignore[attr-defined]


class ReadOnly(_FastTrigger):
    """Fast trigger: fires in the read-only simulation phase."""

    __slots__ = ()


class ReadWrite(_FastTrigger):
    """Fast trigger: fires in the read-write simulation phase."""

    __slots__ = ()


# ---------------------------------------------------------------------------
# Fast mini-scheduler
# ---------------------------------------------------------------------------


class _FastScheduler:
    """Drives a coroutine directly from GPI callbacks.

    Pure-Python fallback for :class:`cocotb._fast_sched._FastScheduler`.
    """

    __slots__ = ("_coro", "_done_trigger", "_callback", "exception", "result")

    def __init__(
        self, coro: Coroutine[Any, None, Any], done_trigger: _FastLoopDone
    ) -> None:
        self._coro = coro
        self._done_trigger = done_trigger
        self._callback = self._on_gpi_callback
        self.exception: BaseException | None = None
        self.result: object = None

    def _dispatch(self, trigger: object) -> None:
        """Register the appropriate GPI callback for *trigger*."""
        cb = self._callback

        if isinstance(trigger, RisingEdge):
            simulator.register_value_change_callback(trigger._sim_hdl, cb, _RISING)
        elif isinstance(trigger, FallingEdge):
            simulator.register_value_change_callback(trigger._sim_hdl, cb, _FALLING)
        elif isinstance(trigger, ValueChange):
            simulator.register_value_change_callback(
                trigger._sim_hdl, cb, _VALUE_CHANGE
            )
        elif isinstance(trigger, ReadOnly):
            simulator.register_readonly_callback(cb)
        elif isinstance(trigger, ReadWrite):
            simulator.register_rwsynch_callback(cb)
        else:
            self.exception = TypeError(
                f"fast scheduler does not support trigger type "
                f"{type(trigger).__qualname__!r}. "
                f"Use cocotb.fast.RisingEdge/FallingEdge/ReadOnly/ReadWrite."
            )
            self._done_trigger._finish()

    def start(self) -> None:
        """Advance the coroutine to its first yield point."""
        try:
            trigger = self._coro.send(None)
            self._dispatch(trigger)
        except StopIteration as e:
            self.result = e.value
            self._done_trigger._finish()
        except BaseException as e:
            self.exception = e
            self._done_trigger._finish()

    def _on_gpi_callback(self) -> None:
        """Called from GPI — advance coroutine to next yield point."""
        try:
            trigger = self._coro.send(None)
            self._dispatch(trigger)
        except StopIteration as e:
            self.result = e.value
            self._done_trigger._finish()
        except BaseException as e:
            self.exception = e
            self._done_trigger._finish()
