# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Cython mini-scheduler for fast async/await loops.

Provides lightweight trigger types and a minimal scheduler that drives
a coroutine directly from GPI callbacks, bypassing cocotb's
Task / EventLoop / TriggerCallback machinery.

The per-cycle overhead is reduced to:
    GPI C callback → Cython dispatch → coro.send() → yield → Cython prime → return

Compared to standard cocotb:
    GPI C callback → GPITrigger._react → _do_callbacks → EventLoop.schedule
    → EventLoop.run → Task._resume → coro.send() → yield → Trigger._register
    → TriggerCallback → _prime → return
"""

from __future__ import annotations

from cocotb import simulator
import cocotb._event_loop
import cocotb._fast_loop as _fast_loop_module


# ---------------------------------------------------------------------------
# GPI edge-type constants (cached at module level to avoid dict lookups)
# ---------------------------------------------------------------------------
cdef int _RISING = simulator.RISING
cdef int _FALLING = simulator.FALLING
cdef int _VALUE_CHANGE = simulator.VALUE_CHANGE


# ---------------------------------------------------------------------------
# Fast trigger base — zero-allocation __await__ protocol
# ---------------------------------------------------------------------------

cdef class _FastTrigger:
    """Base for fast triggers.

    Implements a reusable ``__await__`` protocol: the trigger object itself
    acts as its own iterator, yielding itself exactly once per ``await``.
    No intermediate objects are allocated.
    """
    cdef bint _iter_started

    def __await__(self):
        self._iter_started = False
        return self

    def __iter__(self):
        return self

    def __next__(self):
        if self._iter_started:
            raise StopIteration(self)
        self._iter_started = True
        return self


# ---------------------------------------------------------------------------
# Concrete trigger types
# ---------------------------------------------------------------------------

cdef class RisingEdge(_FastTrigger):
    """Fast trigger: fires on the rising edge of a signal.

    Create once and reuse across iterations::

        rising = fast.RisingEdge(dut.clk)
        for i in range(N):
            await rising
    """
    cdef object _sim_hdl

    def __init__(self, handle):
        self._sim_hdl = handle._handle


cdef class FallingEdge(_FastTrigger):
    """Fast trigger: fires on the falling edge of a signal."""
    cdef object _sim_hdl

    def __init__(self, handle):
        self._sim_hdl = handle._handle


cdef class ValueChange(_FastTrigger):
    """Fast trigger: fires on any value change of a signal."""
    cdef object _sim_hdl

    def __init__(self, handle):
        self._sim_hdl = handle._handle


cdef class ReadOnly(_FastTrigger):
    """Fast trigger: fires in the read-only simulation phase."""
    pass


cdef class ReadWrite(_FastTrigger):
    """Fast trigger: fires in the read-write simulation phase."""
    pass


# ---------------------------------------------------------------------------
# Fast mini-scheduler
# ---------------------------------------------------------------------------

cdef class _FastScheduler:
    """Drives a coroutine directly from GPI callbacks.

    Replaces cocotb's Task + EventLoop + Trigger dispatch chain with a
    single Cython object that:

    1. Calls ``coro.send(None)`` to advance the coroutine
    2. Inspects the yielded trigger
    3. Registers the appropriate GPI callback
    4. When the callback fires, goto 1

    The ``_done_trigger`` is a :class:`~cocotb._fast_loop._FastLoopDone`
    GPITrigger that fires in the ReadOnly phase when the coroutine
    finishes, properly resuming the outer cocotb Task.
    """
    cdef object _coro
    cdef object _done_trigger
    cdef object _callback       # cached bound method (avoids allocation per cycle)
    cdef str _pending_phase     # phase the next callback will fire in
    cdef public object exception
    cdef public object result

    def __init__(self, coro, done_trigger):
        self._coro = coro
        self._done_trigger = done_trigger
        self._callback = self._on_gpi_callback
        self._pending_phase = ""
        self.exception = None
        self.result = None

    cdef void _dispatch(self, object trigger):
        """Register the appropriate GPI callback for *trigger*."""
        cdef object cb = self._callback

        if isinstance(trigger, RisingEdge):
            self._pending_phase = ""
            simulator.register_value_change_callback(
                (<RisingEdge>trigger)._sim_hdl, cb, _RISING)

        elif isinstance(trigger, FallingEdge):
            self._pending_phase = ""
            simulator.register_value_change_callback(
                (<FallingEdge>trigger)._sim_hdl, cb, _FALLING)

        elif isinstance(trigger, ValueChange):
            self._pending_phase = ""
            simulator.register_value_change_callback(
                (<ValueChange>trigger)._sim_hdl, cb, _VALUE_CHANGE)

        elif isinstance(trigger, ReadOnly):
            self._pending_phase = "readonly"
            simulator.register_readonly_callback(cb)

        elif isinstance(trigger, ReadWrite):
            self._pending_phase = "readwrite"
            simulator.register_rwsynch_callback(cb)

        else:
            self.exception = TypeError(
                f"fast scheduler does not support trigger type "
                f"{type(trigger).__qualname__!r}. "
                f"Use cocotb.fast.RisingEdge/FallingEdge/ReadOnly/ReadWrite."
            )
            self._done_trigger._finish()

    def start(self):
        """Advance the coroutine to its first yield point and register the callback."""
        try:
            trigger = self._coro.send(None)
            self._dispatch(trigger)
        except StopIteration as e:
            self.result = e.value
            self._done_trigger._finish()
        except BaseException as e:
            self.exception = e
            self._done_trigger._finish()

    def _on_gpi_callback(self):
        """Called from GPI — advance coroutine to next yield point."""
        # Update phase tracking so SignalProxy can guard against
        # writes in the ReadOnly phase.
        _fast_loop_module._fast_phase = self._pending_phase
        try:
            trigger = self._coro.send(None)
            self._dispatch(trigger)
        except StopIteration as e:
            self.result = e.value
            _fast_loop_module._fast_phase = ""
            self._done_trigger._finish()
        except BaseException as e:
            self.exception = e
            _fast_loop_module._fast_phase = ""
            self._done_trigger._finish()
        # Pump the cocotb event loop so other tasks can make progress.
        # This matches GPITrigger._react() which calls run() after
        # _do_callbacks().  When no other tasks are queued, this is
        # essentially a no-op (empty deque check).
        cocotb._event_loop._inst.run()
