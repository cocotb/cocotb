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
