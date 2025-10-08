from __future__ import annotations

import cocotb
from cocotb.triggers import FallingEdge, RisingEdge, Timer, ValueChange


async def clock_gen(signal, num):
    for _ in range(num):
        signal.value = 0
        await Timer(5, "ns")
        signal.value = 1
        await Timer(5, "ns")


class DualMonitor:
    def __init__(self, edge, signal):
        self.edge_type = edge
        self.monitor_edges = [0, 0]
        self.signal = signal

    async def signal_mon(self, signal, idx, edge):
        while True:
            await edge(signal)
            self.monitor_edges[idx] += 1

    async def start(self):
        clock_edges = 10

        cocotb.start_soon(clock_gen(self.signal, clock_edges))
        _ = cocotb.start_soon(self.signal_mon(self.signal, 0, self.edge_type))
        _ = cocotb.start_soon(self.signal_mon(self.signal, 1, self.edge_type))

        await Timer(100, "ns")

        for mon in self.monitor_edges:
            assert mon, "Monitor saw nothing"


@cocotb.test()
async def issue_348_rising(dut):
    """Start two monitors on RisingEdge"""
    await DualMonitor(RisingEdge, dut.clk).start()


@cocotb.test()
async def issue_348_falling(dut):
    """Start two monitors on FallingEdge"""
    await DualMonitor(FallingEdge, dut.clk).start()


@cocotb.test()
async def issue_348_either(dut):
    """Start two monitors on ValueChange"""
    await DualMonitor(ValueChange, dut.clk).start()
