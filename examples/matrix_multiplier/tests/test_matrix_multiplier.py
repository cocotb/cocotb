# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import math
import os
from random import getrandbits

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.monitors import BusMonitor
from cocotb.regression import TestFactory
from cocotb.scoreboard import Scoreboard
from cocotb.triggers import RisingEdge, ReadOnly

NUM_SAMPLES = int(os.environ.get('NUM_SAMPLES', 3000))
DATA_WIDTH = int(os.environ['DATA_WIDTH'])
A_ROWS = int(os.environ['A_ROWS'])
B_COLUMNS = int(os.environ['B_COLUMNS'])
A_COLUMNS_B_ROWS = int(os.environ['A_COLUMNS_B_ROWS'])


class MatrixMonitor(BusMonitor):
    """Base class for monitoring inputs/outputs of Matrix Multiplier."""
    def __init__(self, dut, callback=None, event=None):
        super().__init__(dut, "", dut.clk_i, callback=callback, event=event)


class MatrixInMonitor(MatrixMonitor):
    """Monitor inputs to Matrix Multiplier module.

    Generate expected results for each multiplication operation.
    """
    _signals = {"A": "a_i", "B": "b_i", "valid": "valid_i"}

    async def _monitor_recv(self):
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()

            if self.bus.valid.value:
                a_matrix = self.bus.A.value
                b_matrix = self.bus.B.value

                # Calculate the expected result of C
                c_expected = [
                    BinaryValue(
                        sum(
                            [
                                a_matrix[(i * A_COLUMNS_B_ROWS) + n] * b_matrix[(n * B_COLUMNS) + j]
                                for n in range(A_COLUMNS_B_ROWS)
                            ]
                        ),
                        n_bits=(DATA_WIDTH * 2) + math.ceil(math.log2(A_COLUMNS_B_ROWS)),
                        bigEndian=False
                    )
                    for i in range(A_ROWS)
                    for j in range(B_COLUMNS)
                ]

                self._recv(c_expected)


class MatrixOutMonitor(MatrixMonitor):
    """Monitor outputs from Matrix Multiplier module.

    Capture result matrix for each multiplication operation.
    """
    _signals = {"C": "c_o", "valid": "valid_o"}

    async def _monitor_recv(self):
        while True:
            await RisingEdge(self.clock)
            await ReadOnly()

            if self.bus.valid.value:
                c_actual = self.bus.C.value
                self._recv(c_actual)


async def test_multiply(dut, a_data, b_data):
    """Test multiplication of many matrices."""

    cocotb.fork(Clock(dut.clk_i, 10, units='ns').start())

    # Configure Scoreboard to compare module results to expected
    expected_output = []

    in_monitor = MatrixInMonitor(dut, callback=expected_output.append)
    out_monitor = MatrixOutMonitor(dut)

    scoreboard = Scoreboard(dut)
    scoreboard.add_interface(out_monitor, expected_output)

    # Initial values
    dut.valid_i <= 0
    dut.a_i <= create_a(lambda x: 0)
    dut.b_i <= create_b(lambda x: 0)

    # Reset DUT
    dut.reset_i <= 1
    for _ in range(3):
        await RisingEdge(dut.clk_i)
    dut.reset_i <= 0

    # Do multiplication operations
    for A, B in zip(a_data(), b_data()):
        await RisingEdge(dut.clk_i)
        dut.a_i <= A
        dut.b_i <= B
        dut.valid_i <= 1

        await RisingEdge(dut.clk_i)
        dut.valid_i <= 0

    await RisingEdge(dut.clk_i)

    raise scoreboard.result


def create_matrix(func, rows, cols):
    return [func(DATA_WIDTH) for row in range(rows) for col in range(cols)]


def create_a(func):
    return create_matrix(func, A_ROWS, A_COLUMNS_B_ROWS)


def create_b(func):
    return create_matrix(func, A_COLUMNS_B_ROWS, B_COLUMNS)


def gen_a(num_samples=NUM_SAMPLES, func=getrandbits):
    """Generate random matrix data for A"""
    for _ in range(num_samples):
        yield create_a(func)


def gen_b(num_samples=NUM_SAMPLES, func=getrandbits):
    """Generate random matrix data for B"""
    for _ in range(num_samples):
        yield create_b(func)


factory = TestFactory(test_multiply)
factory.add_option('a_data', [gen_a])
factory.add_option('b_data', [gen_b])
factory.generate_tests()
