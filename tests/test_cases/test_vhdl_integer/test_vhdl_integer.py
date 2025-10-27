# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import cocotb
from cocotb.triggers import Combine

SIM_NAME = cocotb.SIM_NAME.lower()


async def wait_value_change(signal, expected_value) -> None:
    await signal.value_change
    current_value = signal.value
    assert current_value == expected_value, (
        f"Signal {signal} current value {current_value} didn't match expected value {expected_value}"
    )


@cocotb.test(timeout_time=15, timeout_unit="ns")
async def vhdl_integer_valuechange(dut) -> None:
    dut.i_int.value = 0

    await Combine(
        cocotb.start_soon(wait_value_change(dut.o_int, 0)),
        cocotb.start_soon(wait_value_change(dut.s_int, 1)),
    )


@cocotb.xfail(
    SIM_NAME.startswith("ghdl"),
    raises=AttributeError,
    reason="GHDL is unable to access record signals (gh-2591)",
)
@cocotb.test(timeout_time=15, timeout_unit="ns")
async def vhdl_record_integer_valuechange(dut) -> None:
    a_val = dut.s_ints.a.value
    b_val = dut.s_ints.b.value

    await Combine(
        cocotb.start_soon(wait_value_change(dut.s_ints.a, a_val + 1)),
        cocotb.start_soon(wait_value_change(dut.s_ints.b, b_val + 1)),
    )
