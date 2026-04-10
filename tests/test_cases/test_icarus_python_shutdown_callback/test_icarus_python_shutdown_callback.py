# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Regression for Icarus shutdown vs. embedded Python.

Icarus Verilog may schedule further VPI events after cocotb has finalized the
interpreter. Without handling that in ``handle_gpi_callback``, ``vvp`` can
SIGSEGV in ``PyGILState_Ensure()`` even when all cocotb tests passed.

This module intentionally stays minimal so the failure mode is a non-zero exit
from ``vvp`` / missing ``results.xml``, not a Python assertion.
"""

from __future__ import annotations

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_exit_cleanly_after_finalize(_dut) -> None:
    await Timer(1, unit="ns")
