# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Fast-loop API for tight signal read/write loops.

Two styles of fast loop are available:

**Callback style** (:func:`run_cycles`):
    Maximum speed, single callback per edge, no coroutine overhead.

**Async/await style** (:func:`run`):
    Familiar ``async/await`` syntax with multiple await points per cycle,
    driven by a lightweight Cython mini-scheduler instead of cocotb's
    full Task/EventLoop/Trigger machinery.

Both styles use :class:`SignalProxy` for direct GPI signal access
without :class:`~cocotb.types.Logic` / :class:`~cocotb.types.LogicArray`
construction overhead.

Usage (async/await style)::

    from cocotb import fast

    proxy = fast.SignalProxy(dut.data)
    rising = fast.RisingEdge(dut.clk)
    ro = fast.ReadOnly()


    async def inner():
        for i in range(1_000_000):
            proxy.set_int(i & 0xFF)
            await rising
            await ro
            val = proxy.get_int()


    await fast.run(inner())

.. _fast-behavioral-differences:

Behavioral Differences from Standard cocotb
============================================

The fast scheduler is a lightweight replacement for cocotb's full
Task / EventLoop / Trigger machinery.  It achieves its speedup by
skipping several layers of the standard scheduler.  This introduces
the following behavioral differences that users should be aware of:

**Immediate signal writes (no write batching)**
    :meth:`SignalProxy.set_int` and :meth:`SignalProxy.set_binstr`
    call the GPI ``set_signal_val_*`` functions immediately via a
    ``DEPOSIT`` action.  Standard cocotb defers inertial (deposit)
    writes to the ReadWrite phase and batches multiple writes to the
    same signal into a single GPI call.  In the fast API, every
    ``set_int`` call hits the simulator immediately.  This requires
    ``COCOTB_TRUST_INERTIAL_WRITES=1`` for simulators that do not
    handle inertial writes correctly.

    Writes during the ReadOnly phase **are** detected and raise
    :class:`RuntimeError`, matching standard cocotb behavior.

**No interaction with cocotb's event loop**
    While a fast loop is running, cocotb's :class:`~cocotb.EventLoop`
    is **not** pumped.  Other cocotb tasks (started via
    :func:`~cocotb.start_soon`) will not make progress until the fast
    loop completes and control returns to the standard scheduler.  Do
    not mix concurrent cocotb tasks with fast loops that expect those
    tasks to advance in lock-step.

**``current_gpi_trigger()`` is not updated**
    The fast scheduler does **not** set
    :func:`cocotb._gpi_triggers.current_gpi_trigger`.  Code outside
    the fast loop that relies on this function to determine the
    current simulation phase will see stale values while a fast loop
    is active.  Within the fast loop, :class:`SignalProxy` uses its
    own phase tracking for the ReadOnly write guard.

**No ``_apply_scheduled_writes()`` on ReadWrite**
    Standard cocotb's ``ReadWrite._do_callbacks()`` flushes any
    deferred writes queued by ``dut.signal.value = X`` before resuming
    tasks.  The fast scheduler's ``ReadWrite`` trigger does **not**
    call ``_apply_scheduled_writes()``.  If you mix standard
    ``dut.signal.value`` assignments with fast ``await ReadWrite()``,
    the deferred writes may not be applied at the expected time.
    Use :meth:`SignalProxy.set_int` exclusively inside fast loops.

**No phase-transition guards on triggers**
    Standard cocotb raises :class:`RuntimeError` for illegal
    transitions such as ``await ReadOnly()`` while already in the
    ReadOnly phase, or ``await ReadWrite()`` from ReadOnly.  The fast
    scheduler does not enforce these guards.  Awaiting an illegal
    transition will register the GPI callback, and the resulting
    behavior is simulator-dependent.

**Single-coroutine execution only**
    The fast scheduler drives exactly one coroutine.  There is no
    support for ``start_soon``, ``Combine``, ``First``, or any form
    of concurrent task execution within a fast loop.  If you need
    concurrency, structure the code so that the concurrent portion
    runs under the standard cocotb scheduler and only the tight inner
    loop uses the fast API.

**Supported triggers are limited**
    Only :class:`RisingEdge`, :class:`FallingEdge`, :class:`ReadOnly`,
    :class:`ReadWrite`, and :class:`ValueChange` are supported.
    :class:`~cocotb.triggers.Timer`, :class:`~cocotb.triggers.First`,
    :class:`~cocotb.triggers.Combine`, and other standard triggers
    will raise :class:`TypeError` at runtime.
"""

from __future__ import annotations

import logging
from collections.abc import Coroutine
from typing import Any

from cocotb._fast_loop import SignalProxy, _FastLoopDone, run_cycles

# Import from Cython extension if available, otherwise pure Python fallback.
try:
    from cocotb._fast_sched import (
        FallingEdge,
        ReadOnly,
        ReadWrite,
        RisingEdge,
        ValueChange,
        _FastScheduler,
    )
except ImportError:
    from cocotb._fast_sched_py import (  # type: ignore[no-redef]
        FallingEdge,
        ReadOnly,
        ReadWrite,
        RisingEdge,
        ValueChange,
        _FastScheduler,
    )

_log = logging.getLogger(__name__)

__all__ = [
    "FallingEdge",
    "ReadOnly",
    "ReadWrite",
    "RisingEdge",
    "SignalProxy",
    "ValueChange",
    "run",
    "run_cycles",
]


async def run(coro: Coroutine[Any, None, Any]) -> Any:
    """Run an async coroutine on the fast mini-scheduler.

    The coroutine is driven directly by GPI callbacks, bypassing cocotb's
    Task / EventLoop / TriggerCallback machinery.  The coroutine may
    ``await`` any of the fast trigger types (:class:`RisingEdge`,
    :class:`FallingEdge`, :class:`ReadOnly`, :class:`ReadWrite`,
    :class:`ValueChange`).

    When the coroutine finishes (or raises), control returns to the
    ``await``-ing cocotb Task in the ReadOnly simulation phase.

    Args:
        coro: A coroutine object (the result of calling an ``async def``).

    Returns:
        The return value of the coroutine.

    Raises:
        Exception: Any exception raised inside the coroutine is
            re-raised in the calling cocotb Task.
        TypeError: If the coroutine yields a trigger type not supported
            by the fast scheduler.

    Usage::

        async def inner():
            rising = RisingEdge(dut.clk)
            for i in range(1_000_000):
                proxy.set_int(i)
                await rising


        result = await fast.run(inner())
    """
    done_trigger = _FastLoopDone()
    sched = _FastScheduler(coro, done_trigger)
    sched.start()

    # Suspend this cocotb Task until the inner coroutine finishes.
    await done_trigger

    if sched.exception is not None:
        raise sched.exception

    return sched.result
