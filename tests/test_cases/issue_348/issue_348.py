import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Timer, Edge, RisingEdge, FallingEdge, Join
from cocotb.result import TestFailure, ReturnValue

import sys

@cocotb.coroutine
def clock_gen(signal, num):
    for x in range(num):
        signal <= 0
        yield Timer(500)
        signal <= 1
        yield Timer(500)

@cocotb.coroutine
def signal_mon(signal, idx, edge):
    log = SimLog("cocotb.signal_mon.%d.%s" % (idx, signal._name))
    value = signal.value

    edges = 0

    while True:
        yield edge(signal)
        edges += 1

    raise ReturnValue(edges)

class DualMonitor:
    def __init__(self, edge, signal):
        self.log = SimLog("cocotb.%s.%s" % (edge, signal))
        self.edge_type = edge
        self.monitor_edges = [0, 0]
        self.signal = signal

    @cocotb.coroutine
    def signal_mon(self, signal, idx, edge):
        while True:
            yield edge(signal)
            self.monitor_edges[idx] += 1

    @cocotb.coroutine
    def start(self):
        clock_edges = 10

        cocotb.fork(clock_gen(self.signal, clock_edges))
        first = cocotb.fork(self.signal_mon(self.signal, 0, self.edge_type))
        second = cocotb.fork(self.signal_mon(self.signal, 1, self.edge_type))

        yield Timer(10000)

        for mon in self.monitor_edges:
            if not mon:
                raise TestFailure("Monitor saw nothing")



@cocotb.test()
def issue_348_rising(dut):
    """ Start two monitors on RisingEdge """
    yield DualMonitor(RisingEdge, dut.clk).start()

@cocotb.test()
def issue_348_falling(dut):
    """ Start two monitors on FallingEdge """
    yield DualMonitor(FallingEdge, dut.clk).start()

@cocotb.test()
def issue_348_either(dut):
    """ Start two monitors on Edge """
    yield DualMonitor(Edge, dut.clk).start()
