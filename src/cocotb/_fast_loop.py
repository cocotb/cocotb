# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Fast-loop API: bypass Python coroutine overhead for tight signal loops.

Provides :class:`SignalProxy` for lightweight signal access and
:func:`run_cycles` for running a user callback on each clock edge
without per-cycle coroutine suspend/resume.
"""

from __future__ import annotations

from collections.abc import Callable

import cocotb._event_loop
from cocotb import simulator
from cocotb._gpi_triggers import GPITrigger
from cocotb.handle import SimHandleBase

# DEPOSIT action value from _GPISetAction enum (handle.py)
_DEPOSIT: int = 0

# Phase tracking for the fast scheduler.
# Set by _FastScheduler._on_gpi_callback to indicate which simulation phase
# the fast loop is currently executing in.  SignalProxy checks this to prevent
# writes during the ReadOnly phase.
_fast_phase: str = ""
"""Current fast-scheduler phase: ``"readonly"``, ``"readwrite"``, or ``""``."""


class SignalProxy:
    """Lightweight signal accessor that bypasses Logic/LogicArray creation.

    Wraps a :class:`~cocotb.handle.SimHandleBase` and provides direct
    GPI read/write methods that return raw Python ints and strings,
    avoiding the overhead of :class:`~cocotb.types.Logic`,
    :class:`~cocotb.types.LogicArray`, and :class:`~cocotb.types.Range`
    construction on every access.

    Args:
        handle: A cocotb simulation handle (e.g. ``dut.signal``).

    Usage::

        proxy = SignalProxy(dut.my_signal)
        val = proxy.get_int()
        proxy.set_int(42)
    """

    __slots__ = ("_handle",)

    def __init__(self, handle: SimHandleBase) -> None:
        self._handle: simulator.sim_obj = handle._handle

    def get_int(self) -> int:
        """Read the signal value as an integer via ``gpi_get_signal_value_long``."""
        return self._handle.get_signal_val_long()

    def get_binstr(self) -> str:
        """Read the signal value as a binary string via ``gpi_get_signal_value_binstr``."""
        return self._handle.get_signal_val_binstr()

    def set_int(self, value: int) -> None:
        """Write an integer value to the signal via ``gpi_set_signal_value_int`` (DEPOSIT).

        .. note::
            This performs an immediate deposit write, bypassing cocotb's
            write-scheduling machinery. For correct behavior on simulators
            that don't support inertial writes natively, set the environment
            variable ``COCOTB_TRUST_INERTIAL_WRITES=1``.

        Raises:
            RuntimeError: If called during the ReadOnly simulation phase.
        """
        if _fast_phase == "readonly":
            raise RuntimeError("Attempting to set a value during the ReadOnly phase.")
        self._handle.set_signal_val_int(_DEPOSIT, value)

    def set_binstr(self, value: str) -> None:
        """Write a binary string value to the signal via ``gpi_set_signal_value_binstr`` (DEPOSIT).

        .. note::
            Same caveats as :meth:`set_int` regarding inertial writes.

        Raises:
            RuntimeError: If called during the ReadOnly simulation phase.
        """
        if _fast_phase == "readonly":
            raise RuntimeError("Attempting to set a value during the ReadOnly phase.")
        self._handle.set_signal_val_binstr(_DEPOSIT, value)


class _FastLoopDone(GPITrigger):
    """One-shot trigger that fires in the ReadOnly phase when a fast loop completes.

    This is an internal implementation detail of :func:`run_cycles`.
    It behaves as a proper :class:`GPITrigger` so that ``_react`` correctly
    sets ``_current_gpi_trigger`` and runs the cocotb event loop.
    """

    def _prime(self) -> None:
        # Not primed immediately — _finish() will register the actual callback.
        pass

    def _unprime(self) -> None:
        if self._cbhdl is not None:
            self._cbhdl.deregister()
            self._cbhdl = None

    def _finish(self) -> None:
        """Schedule this trigger to fire in the ReadOnly phase."""
        self._cbhdl = simulator.register_readonly_callback(self._react)


async def run_cycles(
    clock_signal: SimHandleBase,
    step_fn: Callable[[int], bool],
    *,
    edge: int = simulator.RISING,
) -> int:
    """Run *step_fn* once per clock edge, bypassing the Python event loop.

    Registers a GPI value-change callback on *clock_signal* and calls
    ``step_fn(cycle)`` on each matching edge. The function runs entirely
    outside the cocotb scheduler — no coroutine suspend/resume, no trigger
    objects, no :class:`~cocotb.types.Logic` construction per cycle.

    When *step_fn* returns ``False`` (or a falsy value), the loop ends
    and control returns to the ``await``-ing coroutine in the ReadOnly phase.

    Args:
        clock_signal: The clock handle to monitor (e.g. ``dut.clk``).
        step_fn: A callable ``(cycle: int) -> bool``. Called with the
            current cycle count (starting at 0). Return ``True`` to
            continue, ``False`` to stop.
        edge: GPI edge type — one of ``simulator.RISING``,
            ``simulator.FALLING``, or ``simulator.VALUE_CHANGE``.
            Defaults to ``simulator.RISING``.

    Returns:
        The number of cycles executed (i.e. the number of times
        *step_fn* was called).

    Raises:
        Exception: Any exception raised by *step_fn* is re-raised
            in the ``await``-ing coroutine after the loop exits.

    Usage::

        from cocotb.fast import SignalProxy, run_cycles

        proxy = SignalProxy(dut.data)


        def step(cycle: int) -> bool:
            proxy.set_int(cycle & 0xFF)
            _ = proxy.get_int()
            return cycle < 999_999


        total = await run_cycles(dut.clk, step)
    """
    sim_hdl: simulator.sim_obj = clock_signal._handle
    done_trigger = _FastLoopDone()
    cycle_count = [0]
    exception: list[BaseException | None] = [None]

    def _on_edge() -> None:
        global _fast_phase
        _fast_phase = ""  # Value-change edges are not phase-specific.
        try:
            if step_fn(cycle_count[0]):
                cycle_count[0] += 1
                # GPI callbacks are one-shot; re-register for the next edge.
                simulator.register_value_change_callback(sim_hdl, _on_edge, edge)
            else:
                # step_fn signalled stop — resume the cocotb Task.
                cycle_count[0] += 1  # count the final call
                _fast_phase = ""
                done_trigger._finish()
        except BaseException as exc:
            exception[0] = exc
            _fast_phase = ""
            done_trigger._finish()
        # Pump the cocotb event loop so other tasks can make progress.
        # This matches GPITrigger._react() which calls run() after
        # _do_callbacks().  When no other tasks are queued, this is
        # essentially a no-op (empty deque check).
        cocotb._event_loop._inst.run()

    # Kick off the first callback.
    simulator.register_value_change_callback(sim_hdl, _on_edge, edge)

    # Suspend this coroutine until the loop completes.
    await done_trigger

    if exception[0] is not None:
        raise exception[0]

    return cycle_count[0]
