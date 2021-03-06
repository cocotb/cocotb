# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import math
import os
from random import getrandbits
from typing import Dict, List, Any

import cocotb
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.regression import TestFactory
from cocotb.triggers import RisingEdge
from cocotb.queue import Queue
from cocotb.handle import SimHandleBase

NUM_SAMPLES = int(os.environ.get('NUM_SAMPLES', 3000))
DATA_WIDTH = int(cocotb.top.DATA_WIDTH)
A_ROWS = int(cocotb.top.A_ROWS)
B_COLUMNS = int(cocotb.top.B_COLUMNS)
A_COLUMNS_B_ROWS = int(cocotb.top.A_COLUMNS_B_ROWS)


class DataValidMonitor:
    """
    Reusable Monitor of one-way control flow (data/valid) streaming data interface

    Args
        clk: clock signal
        valid: control signal noting a transaction occured
        datas: named handles to be sampled when transaction occurs
    """

    def __init__(self, clk: SimHandleBase, datas: Dict[str, SimHandleBase], valid: SimHandleBase):
        self.values = Queue[Dict[str, int]]()
        self._clk = clk
        self._datas = datas
        self._valid = valid
        self._coro = None

    def start(self) -> None:
        """Start monitor"""
        if self._coro is not None:
            raise RuntimeError("Monitor already started")
        self._coro = cocotb.fork(self._run())

    def stop(self) -> None:
        """Stop monitor"""
        if self._coro is None:
            raise RuntimeError("Monitor never started")
        self._coro.kill()
        self._coro = None

    async def _run(self) -> None:
        while True:
            await RisingEdge(self._clk)
            if self._valid.value.binstr != '1':
                await RisingEdge(self._valid)
                continue
            self.values.put_nowait(self._sample())

    def _sample(self) -> Dict[str, Any]:
        """
        Samples the data signals and builds a transaction object

        Return value is what is stored in queue. Meant to be overriden by the user.
        """
        return {name: handle.value for name, handle in self._datas.items()}


class MatrixMultiplierTester:
    """
    Reusable checker of a matrix_multiplier instance

    Args
        matrix_multiplier_entity: handle to an instance of matrix_multiplier
    """

    def __init__(self, matrix_multiplier_entity: SimHandleBase):
        self.dut = matrix_multiplier_entity

        self.input_mon = DataValidMonitor(
            clk=self.dut.clk_i,
            valid=self.dut.valid_i,
            datas=dict(
                A=self.dut.a_i,
                B=self.dut.b_i))

        self.output_mon = DataValidMonitor(
            clk=self.dut.clk_i,
            valid=self.dut.valid_o,
            datas=dict(C=self.dut.c_o))

        self._checker = None

    def start(self) -> None:
        """Starts monitors, model, and checker coroutine"""
        if self._checker is not None:
            raise RuntimeError("Monitor already started")
        self.input_mon.start()
        self.output_mon.start()
        self._checker = cocotb.fork(self._check())

    def stop(self) -> None:
        """Stops everything"""
        if self._checker is None:
            raise RuntimeError("Monitor never started")
        self.input_mon.stop()
        self.output_mon.stop()
        self._checker.kill()
        self._checker = None

    def model(self, a_matrix: List[int], b_matrix: List[int]) -> List[int]:
        """Transaction-level model of the matrix multipler as instantiated"""
        A_ROWS = self.dut.A_ROWS.value
        A_COLUMNS_B_ROWS = self.dut.A_COLUMNS_B_ROWS.value
        B_COLUMNS = self.dut.B_COLUMNS.value
        DATA_WIDTH = self.dut.DATA_WIDTH.value
        return [
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

    async def _check(self) -> None:
        while True:
            actual = await self.output_mon.values.get()
            expected_inputs = await self.input_mon.values.get()
            expected = self.model(
                a_matrix=expected_inputs['A'],
                b_matrix=expected_inputs['B'])
            assert actual['C'] == expected


async def test_multiply(dut, a_data, b_data):
    """Test multiplication of many matrices."""

    cocotb.fork(Clock(dut.clk_i, 10, units='ns').start())
    tester = MatrixMultiplierTester(dut)

    dut._log.info("Initialize and reset model")

    # Initial values
    dut.valid_i <= 0
    dut.a_i <= create_a(lambda x: 0)
    dut.b_i <= create_b(lambda x: 0)

    # Reset DUT
    dut.reset_i <= 1
    for _ in range(3):
        await RisingEdge(dut.clk_i)
    dut.reset_i <= 0

    # start tester after reset so we know it's in a good state
    tester.start()

    dut._log.info("Test multiplication operations")

    # Do multiplication operations
    for i, (A, B) in enumerate(zip(a_data(), b_data())):
        await RisingEdge(dut.clk_i)
        dut.a_i <= A
        dut.b_i <= B
        dut.valid_i <= 1

        await RisingEdge(dut.clk_i)
        dut.valid_i <= 0

        if i % 100 == 0:
            dut._log.info("{} / {}".format(i, NUM_SAMPLES))

    await RisingEdge(dut.clk_i)


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
