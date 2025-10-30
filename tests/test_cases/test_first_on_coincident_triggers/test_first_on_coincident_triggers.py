# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import logging
import unittest

import cocotb
from cocotb.triggers import First, RisingEdge, Timer
from cocotb.utils import get_sim_time


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


@cocotb.test()
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
