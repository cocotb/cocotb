import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Timer, RisingEdge, FallingEdge
from cocotb.result import TestFailure, TestSuccess

import sys

@cocotb.coroutine
def clock_gen(signal, num):
    for x in range(num):
        signal <= 0
        yield Timer(500)
        signal <= 1
        yield Timer(500)

class DualMonitor:
    def __init__(self, signal):
        self.log = SimLog("cocotb.%s" % (signal._name))
        self.monitor_edges = [0, 0]
        self.signal = signal

    @cocotb.coroutine
    def signal_mon(self, signal, idx):
        while True:
            result = yield RisingEdge(signal)
            self.log.info("signal_mon called on %s" % result)
            self.monitor_edges[idx] += 1
            
    @cocotb.coroutine
    def signal_mon_both(self, signal, idx):
        while True:
            result = yield [RisingEdge(signal), FallingEdge(signal)]
            self.log.info("signal_mon_both called on %s" % result)
            self.monitor_edges[idx] += 1

    @cocotb.coroutine
    def start(self):
        clock_edges = 10

        cocotb.fork(clock_gen(self.signal, clock_edges))
        yield Timer(1)
        cocotb.fork(self.signal_mon(self.signal, 0))
        cocotb.fork(self.signal_mon_both(self.signal, 1))

        yield Timer(2001)

        self.log.info("signal_mon coroutine saw %d edges" % self.monitor_edges[0])
        self.log.info("signal_mon_both coroutine saw %d edges" % self.monitor_edges[1])
        if self.monitor_edges[1] != self.monitor_edges[0] * 2:
            raise TestFailure("%d is not twice %d" % (self.monitor_edges[1], self.monitor_edges[0]))
        else:
            raise TestSuccess("%d is twice %d" % (self.monitor_edges[1], self.monitor_edges[0]))


@cocotb.test()
def test1(dut):
    """ Start DualMonitor to monitor clock edges """
    yield DualMonitor(dut.clk).start()
