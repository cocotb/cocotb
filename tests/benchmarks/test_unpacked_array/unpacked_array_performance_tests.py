# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os
from pathlib import Path
from time import perf_counter_ns

import cocotb
from cocotb.handle import ArrayObject
from cocotb.triggers import Timer
from cocotb.types import Array, Range

ITERATIONS = 100
MASK = (1 << 64) - 1


@cocotb.test()
async def bulk_write(dut):
    memory = dut.memory
    assert isinstance(memory, ArrayObject)
    left = int(os.environ["MEMORY_LEFT"])
    right = int(os.environ["MEMORY_RIGHT"])
    expected_range = Range(left, "to" if left <= right else "downto", right)
    assert memory.range == expected_range
    size = len(expected_range)
    values = [(i * 0x9E3779B97F4A7C15) & MASK for i in range(size)]
    values[0], values[-1] = 0, MASK
    alternate = [value ^ MASK for value in values]

    def payload(items):
        if os.environ["INPUT_KIND"] == "array":
            return Array(items, Range(size + 42, "downto", 43))
        return items

    inputs = [payload(values), payload(alternate)]
    cached_before = len(memory._sub_handles)
    assert cached_before == 0
    started = perf_counter_ns()
    memory.value = inputs[0]
    first_write_ns = perf_counter_ns() - started
    cached_after_first = len(memory._sub_handles)
    await Timer(1, unit="ns")

    repeated_write_ns = []
    expected_values = values
    if os.environ["WRITE_PHASE"] == "repeated":
        for iteration in range(ITERATIONS):
            selection = iteration % 2
            started = perf_counter_ns()
            memory.value = inputs[selection]
            repeated_write_ns.append(perf_counter_ns() - started)
            await Timer(1, unit="ns")
        expected_values = (values, alternate)[selection]

    cached_after_writes = len(memory._sub_handles)
    result = memory.value
    assert result.range == expected_range
    assert [int(value) for value in result] == expected_values
    for index, expected in zip(expected_range, expected_values):
        assert int(memory[index].value) == expected

    measurements = {
        "first_write_ns": first_write_ns,
        "repeated_write_ns": repeated_write_ns,
        "cached_before": cached_before,
        "cached_after_first": cached_after_first,
        "cached_after_writes_before_readback": cached_after_writes,
        "left": left,
        "right": right,
        "input_kind": os.environ["INPUT_KIND"],
        "write_phase": os.environ["WRITE_PHASE"],
        "word_bits": 64,
    }
    Path(os.environ["MEASUREMENTS_FILE"]).write_text(
        json.dumps(measurements), encoding="utf-8"
    )
