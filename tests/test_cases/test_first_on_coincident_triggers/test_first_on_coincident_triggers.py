# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import os
import unittest

import cocotb
from cocotb.triggers import First, RisingEdge, Timer
from cocotb.utils import get_sim_time

SIM_NAME = cocotb.SIM_NAME.lower()
LANGUAGE = os.environ["TOPLEVEL_LANG"].lower().strip()
VHDL_INTF = os.environ.get("VHDL_GPI_INTERFACE", "fli").strip()


@cocotb.test()
async def test_first_on_coincident_trigger(dut) -> None:
    try:
        with unittest.TestCase().assertLogs(
            "cocotb.scheduler", level=logging.CRITICAL
        ) as logs:
            await First(
                RisingEdge(dut.a),
                RisingEdge(dut.b),
            )
            await Timer(10, "ns")
    except AssertionError:
        pass  # no CRITICAL logs is good
    else:
        # if there are CRITICAL logs, check for the one that indicated the problem
        assert (
            "No coroutines waiting on trigger that fired" not in logs.records[0].message
        )


@cocotb.xfail(
    SIM_NAME.startswith("nvc"),
    reason="NVC doesn't fire second RisingEdge trigger for dut.b when it is registered the same time step that a change occurred (gh-5112)",
)
@cocotb.xfail(
    SIM_NAME.startswith("verilator"),
    reason="Verilator doesn't fire second RisingEdge trigger for dut.b when it is registered the same time step that a change occurred (gh-5112)",
)
@cocotb.xfail(
    SIM_NAME.startswith("riviera"),
    reason="Riviera doesn't fire second RisingEdge trigger for dut.b when it is registered the same time step that a change occurred (gh-5112)",
)
@cocotb.xfail(
    SIM_NAME.startswith("xmsim") and LANGUAGE in ["vhdl"],
    reason="xcelium doesn't fire second RisingEdge trigger for dut.b when it is registered the same time step that a change occurred (gh-5112)",
)
@cocotb.xfail(
    SIM_NAME.startswith("modelsim") and LANGUAGE in ["vhdl"] and VHDL_INTF in ["vhpi"],
    reason="Questa doesn't fire second RisingEdge trigger for dut.b when it is registered the same time step that a change occurred (gh-5112)",
)
@cocotb.skipif(
    SIM_NAME.startswith("modelsim") and LANGUAGE in ["vhdl"] and VHDL_INTF in ["fli"],
    reason="Questa will segfault",
)
@cocotb.xfail(
    SIM_NAME.startswith("ghdl"),
    reason="GHDL doesn't fire second RisingEdge trigger for dut.b when it is registered the same time step that a change occurred (gh-5112)",
)
# Setting timeout because even though GHDL fails the test correctly, it gets stuck and doesn't finish simulation (gh-4997)
@cocotb.test(timeout_time=100, timeout_unit="ns")
async def test_repeated_first_no_missed_edges(dut) -> None:
    """Test that waiting on First() twice will catch both triggers that happen at the same simulation time."""
    a_count = 0
    b_count = 0

    start_time = get_sim_time("ns")
    end_time = start_time + 30

    while True:
        trigger = await First(RisingEdge(dut.a), RisingEdge(dut.b))
        if get_sim_time("ns") > end_time:
            break
        signal = trigger.signal
        cocotb.log.info(f"Fired: {signal._name} at {get_sim_time('ns')}")
        if signal is dut.a:
            a_count += 1
        elif signal is dut.b:
            b_count += 1

    assert a_count == 2
    assert b_count == 2
