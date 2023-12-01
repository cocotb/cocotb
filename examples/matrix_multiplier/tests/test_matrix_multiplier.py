# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0

import math
import os
import sys
from pathlib import Path
from random import getrandbits
from typing import Any, Dict, List

import cocotb
import pytest
from cocotb.binary import BinaryValue
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase
from cocotb.queue import Queue
from cocotb.runner import get_runner
from cocotb.triggers import RisingEdge

NUM_SAMPLES = int(os.environ.get("NUM_SAMPLES", 3000))
if cocotb.simulator.is_running():
    DATA_WIDTH = cocotb.top.DATA_WIDTH.value
    A_ROWS = cocotb.top.A_ROWS.value
    B_COLUMNS = cocotb.top.B_COLUMNS.value
    A_COLUMNS_B_ROWS = cocotb.top.A_COLUMNS_B_ROWS.value


class DataValidMonitor:
    """
    Reusable Monitor of one-way control flow (data/valid) streaming data interface

    Args
        clk: clock signal
        valid: control signal noting a transaction occured
        datas: named handles to be sampled when transaction occurs
    """

    def __init__(
        self, clk: SimHandleBase, datas: Dict[str, SimHandleBase], valid: SimHandleBase
    ):
        self.values = Queue[Dict[str, int]]()
        self._clk = clk
        self._datas = datas
        self._valid = valid
        self._coro = None

    def start(self) -> None:
        """Start monitor"""
        if self._coro is not None:
            raise RuntimeError("Monitor already started")
        self._coro = cocotb.start_soon(self._run())

    def stop(self) -> None:
        """Stop monitor"""
        if self._coro is None:
            raise RuntimeError("Monitor never started")
        self._coro.kill()
        self._coro = None

    async def _run(self) -> None:
        while True:
            await RisingEdge(self._clk)
            if self._valid.value.binstr != "1":
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
            datas=dict(A=self.dut.a_i, B=self.dut.b_i),
        )

        self.output_mon = DataValidMonitor(
            clk=self.dut.clk_i, valid=self.dut.valid_o, datas=dict(C=self.dut.c_o)
        )

        self._checker = None

    def start(self) -> None:
        """Starts monitors, model, and checker coroutine"""
        if self._checker is not None:
            raise RuntimeError("Monitor already started")
        self.input_mon.start()
        self.output_mon.start()
        self._checker = cocotb.start_soon(self._check())

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
                        a_matrix[(i * A_COLUMNS_B_ROWS) + n]
                        * b_matrix[(n * B_COLUMNS) + j]
                        for n in range(A_COLUMNS_B_ROWS)
                    ]
                ),
                n_bits=(DATA_WIDTH * 2) + math.ceil(math.log2(A_COLUMNS_B_ROWS)),
                bigEndian=False,
            )
            for i in range(A_ROWS)
            for j in range(B_COLUMNS)
        ]

    async def _check(self) -> None:
        while True:
            actual = await self.output_mon.values.get()
            expected_inputs = await self.input_mon.values.get()
            expected = self.model(
                a_matrix=expected_inputs["A"], b_matrix=expected_inputs["B"]
            )
            assert actual["C"] == expected


@cocotb.test()
async def multiply_test(dut):
    """Test multiplication of many matrices."""

    cocotb.start_soon(Clock(dut.clk_i, 10, units="ns").start())
    tester = MatrixMultiplierTester(dut)

    dut._log.info("Initialize and reset model")

    # Initial values
    dut.valid_i.value = 0
    dut.a_i.value = create_a(lambda x: 0)
    dut.b_i.value = create_b(lambda x: 0)

    # Reset DUT
    dut.reset_i.value = 1
    for _ in range(3):
        await RisingEdge(dut.clk_i)
    dut.reset_i.value = 0

    # start tester after reset so we know it's in a good state
    tester.start()

    dut._log.info("Test multiplication operations")

    # Do multiplication operations
    for i, (A, B) in enumerate(zip(gen_a(), gen_b())):
        await RisingEdge(dut.clk_i)
        dut.a_i.value = A
        dut.b_i.value = B
        dut.valid_i.value = 1

        await RisingEdge(dut.clk_i)
        dut.valid_i.value = 0

        if i % 100 == 0:
            dut._log.info(f"{i} / {NUM_SAMPLES}")

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


@pytest.mark.skipif(
    os.getenv("SIM", "icarus") == "ghdl",
    reason="Skipping since GHDL doesn't support constants effectively",
)
def test_matrix_multiplier_runner():
    """Simulate the matrix_multiplier example using the Python runner.

    This file can be run directly or via pytest discovery.
    """
    hdl_toplevel_lang = os.getenv("HDL_TOPLEVEL_LANG", "verilog")
    sim = os.getenv("SIM", "icarus")

    proj_path = Path(__file__).resolve().parent.parent

    verilog_sources = []
    vhdl_sources = []
    build_args = []

    if hdl_toplevel_lang == "verilog":
        verilog_sources = [proj_path / "hdl" / "matrix_multiplier.sv"]

        if sim in ["riviera", "activehdl"]:
            build_args = ["-sv2k12"]

    elif hdl_toplevel_lang == "vhdl":
        vhdl_sources = [
            proj_path / "hdl" / "matrix_multiplier_pkg.vhd",
            proj_path / "hdl" / "matrix_multiplier.vhd",
        ]

        if sim in ["questa", "modelsim", "riviera", "activehdl"]:
            build_args = ["-2008"]
    else:
        raise ValueError(
            f"A valid value (verilog or vhdl) was not provided for TOPLEVEL_LANG={hdl_toplevel_lang}"
        )

    extra_args = []
    if sim == "ghdl":
        extra_args = ["--std=08"]

    parameters = {
        "DATA_WIDTH": "32",
        "A_ROWS": 10,
        "B_COLUMNS": 4,
        "A_COLUMNS_B_ROWS": 6,
    }

    # equivalent to setting the PYTHONPATH environment variable
    sys.path.append(str(proj_path / "tests"))

    runner = get_runner(sim)

    runner.build(
        hdl_toplevel="matrix_multiplier",
        verilog_sources=verilog_sources,
        vhdl_sources=vhdl_sources,
        build_args=build_args + extra_args,
        parameters=parameters,
        always=True,
    )

    runner.test(
        hdl_toplevel="matrix_multiplier",
        hdl_toplevel_lang=hdl_toplevel_lang,
        test_module="test_matrix_multiplier",
        test_args=extra_args,
    )


if __name__ == "__main__":
    test_matrix_multiplier_runner()
