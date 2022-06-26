# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import logging
import unittest

import cocotb
from cocotb.triggers import First, RisingEdge, Timer


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
