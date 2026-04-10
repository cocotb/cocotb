# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Regression for Icarus shutdown vs. embedded Python.

Icarus Verilog 13 can deliver VPI callbacks after cocotb has called
``Py_Finalize()``, causing a SIGSEGV in ``PyGILState_Ensure()``.

The crash requires a clock period around 100 ns (100000 sim steps at 1 ps
precision) — the default used by bus-driver packages such as cocotbext-jtag.
Shorter periods (e.g. 10 ns) change the event alignment at shutdown and avoid
the problematic code path.

Without the ``Py_IsInitialized()`` guard in ``handle_gpi_callback``, ``vvp``
segfaults right after the PASS summary.  The Makefile forces ``WAVES=0`` to
match the original repro.
"""

from __future__ import annotations

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer


async def _run(dut, *, edges: int) -> None:
    Clock(dut.clk, 100, unit="ns").start(start_high=False)
    for _ in range(edges):
        await RisingEdge(dut.clk)
    await Timer(50, unit="ns")


@cocotb.test()
async def test_shutdown_a(dut) -> None:
    await _run(dut, edges=40)


@cocotb.test()
async def test_shutdown_b(dut) -> None:
    await _run(dut, edges=35)


@cocotb.test()
async def test_shutdown_c(dut) -> None:
    await _run(dut, edges=45)
