# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import First, RisingEdge, Timer


class MonitorChange:
    def __init__(self, signal, valid, expect_change=True) -> None:
        self.monitor_process = None
        self.signal = signal
        self.valid = valid
        self.expect_change = expect_change

    def __enter__(self):
        self.start_monitor()

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.assert_change()
            return True
        else:
            self.stop_monitor()
            return False

    async def _monitor_req_design_update(self):
        update = False

        while not update:
            await First(RisingEdge(self.signal), RisingEdge(self.valid))
            update = self.signal.value == 1 and self.valid.value == 1

        assert self.expect_change, "Unexpected change happened"

    def stop_monitor(self):
        if self.monitor_process is not None:
            self.monitor_process.cancel()
        self.monitor_process = None

    def start_monitor(self):
        self.stop_monitor()
        self.monitor_process = cocotb.start_soon(self._monitor_req_design_update())

    def assert_change(self):
        is_ok = True
        if not (self.monitor_process is None or self.monitor_process.done()):
            is_ok = not self.expect_change
        self.stop_monitor()
        assert is_ok, "Change SHOULD have happened"


async def init_dut(dut):
    dut.i_rst_n.value = 1
    dut.i_clk.value = 0
    dut.i_trg.value = 0
    dut.i_valid.value = 0
    dut.i_cnt.value = 0
    await Timer(1)
    dut.i_rst_n.value = 0
    await Timer(10, "ns")
    dut.i_rst_n.value = 1
    clk = Clock(dut.i_clk, 1, "ns")
    clk.start()
    return clk


@cocotb.test()
async def buggy(dut):
    clk = await init_dut(dut)

    async def stuff(dut):
        with (
            MonitorChange(dut.o_pulse, dut.o_valid, expect_change=False),
            MonitorChange(dut.i_trg, dut.o_valid, expect_change=False),
        ):
            await Timer(10, "us")

    coro = cocotb.start_soon(stuff(dut))

    await Timer(5, "ns")
    await RisingEdge(dut.i_clk)
    dut.i_cnt.value = 5
    dut.i_trg.value = 1
    dut.i_valid.value = 0
    await RisingEdge(dut.i_clk)
    dut.i_trg.value = 0

    await RisingEdge(dut.o_pulse)
    clk.stop()
    coro.cancel()
    await Timer(1, "us")


@cocotb.test()
async def basic_ok(dut):
    clk = await init_dut(dut)

    with MonitorChange(dut.o_pulse, dut.o_valid, expect_change=True):
        await Timer(5, "ns")
        await RisingEdge(dut.i_clk)
        dut.i_cnt.value = 5
        dut.i_trg.value = 1
        dut.i_valid.value = 1
        await RisingEdge(dut.i_clk)
        dut.i_trg.value = 0

        await RisingEdge(dut.o_pulse)
        await Timer(10, "ns")

    await Timer(10, "ns")
    clk.stop()
