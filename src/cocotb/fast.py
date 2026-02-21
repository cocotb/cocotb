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

**Immediate signal writes (no write batching)** *(by design)*
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

    This is inherent to the design — adding deferred write batching
    would reintroduce the overhead being eliminated.  When
    ``COCOTB_TRUST_INERTIAL_WRITES=1`` is set, standard cocotb also
    writes immediately, so behavior is identical on trusted simulators.

**``current_gpi_trigger()`` is updated** *(resolved)*
    The fast scheduler sets
    :func:`cocotb._gpi_triggers.current_gpi_trigger` to the standard
    singleton ``ReadOnly()`` / ``ReadWrite()`` instances when entering
    those phases.  Concurrent standard cocotb tasks see correct phase
    awareness for write guards.

**``_apply_scheduled_writes()`` called on ReadWrite** *(resolved)*
    The fast scheduler calls ``cocotb.handle._apply_scheduled_writes()``
    when entering the ReadWrite phase, matching standard
    ``ReadWrite._do_callbacks()`` behavior.  Deferred writes queued by
    ``dut.signal.value = X`` from concurrent tasks are flushed before
    the fast coroutine resumes.

**Phase-transition guards enforced** *(resolved)*
    The fast scheduler raises :class:`RuntimeError` for illegal
    transitions such as ``await ReadOnly()`` while already in the
    ReadOnly phase, or ``await ReadWrite()`` from ReadOnly, matching
    standard cocotb behavior.

**Single-coroutine execution only** *(by design)*
    The fast scheduler drives exactly one coroutine.  There is no
    support for ``start_soon``, ``Combine``, ``First``, or any form
    of concurrent task execution within a fast loop.  If you need
    concurrency, structure the code so that the concurrent portion
    runs under the standard cocotb scheduler and only the tight inner
    loop uses the fast API.  Concurrent tasks started *outside* the
    fast loop (e.g. Clock drivers) work normally since the cocotb
    event loop is pumped after each step.

**Supported triggers are limited** *(partially addressable)*
    Only :class:`RisingEdge`, :class:`FallingEdge`, :class:`ReadOnly`,
    :class:`ReadWrite`, and :class:`ValueChange` are supported.
    :class:`~cocotb.triggers.Timer`, :class:`~cocotb.triggers.First`,
    :class:`~cocotb.triggers.Combine`, and other standard triggers
    will raise :class:`TypeError` at runtime.

    ``Timer`` could be added via ``register_timed_callback``.
    ``First`` / ``Combine`` require multi-trigger coordination that
    conflicts with the single-dispatch design.
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
    from cocotb._fast_sched_py import (  # type: ignore[assignment]
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
