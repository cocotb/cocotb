'''Copyright (c) 2016 Technische Universitaet Dresden, Germany
Chair for VLSI-Design, Diagnostic and Architecture
Author: Martin Zabel
All rights reserved.

Structure of this testbench is based on Endian Swapper Example delivered with
Cocotb.'''

#import traceback
import random

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.monitors import Monitor
from cocotb.drivers import BitDriver
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory
from cocotb.scoreboard import Scoreboard
from cocotb.result import TestFailure, TestSuccess

class BitMonitor(Monitor):
    '''Observes single input or output of DUT.'''
    def __init__(self, name, signal, clk, callback=None, event=None):
        self.name = name
        self.signal = signal
        self.clk = clk
        Monitor.__init__(self, callback, event)
        
    @coroutine
    def _monitor_recv(self):
        clkedge = RisingEdge(self.clk)

        while True:
            yield clkedge
            vec = self.signal.value
            self._recv(vec)

def input_gen():
    while True:
        yield random.randint(1,5), random.randint(1,5)
        
class DFF_TB(object):
    def __init__(self, dut, init_val):
        self.dut = dut
        self.stopped = False
        self.input_drv = BitDriver(dut.d, dut.c, input_gen())
        self.output_mon = BitMonitor("output", dut.q, dut.c)
        
        # Create a scoreboard on the outputs
        self.expected_output = [ init_val ]
        self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_mon, self.expected_output)

        # Reconstruct the input transactions from the pins
        # and send them to our 'model'
        self.input_mon = BitMonitor("input", dut.d, dut.c,
                                    callback=self.model)

    def model(self, transaction):
        '''Model the DUT based on the input transaction.'''
        if not self.stopped:
            self.expected_output.append(transaction)

    def start(self):
        self.input_drv.start()

    def stop(self):
        self.input_drv.stop()
        self.stopped = True

@cocotb.coroutine
def clock_gen(signal):
    while True:
        signal <= 0
        yield Timer(5000) # ps
        signal <= 1
        yield Timer(5000) # ps

@cocotb.coroutine
def run_test(dut):
    cocotb.fork(clock_gen(dut.c))
    tb = DFF_TB(dut, BinaryValue(0,1))
    clkedge = RisingEdge(dut.c)
    
    tb.start()
    for i in range(100):
        yield clkedge
        
    tb.stop()
    yield clkedge
    
    raise tb.scoreboard.result

factory = TestFactory(run_test)
factory.generate_tests()
