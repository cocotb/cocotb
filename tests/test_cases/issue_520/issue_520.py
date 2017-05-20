import cocotb
from cocotb.log import SimLog
from cocotb.triggers import Timer, Edge, RisingEdge, FallingEdge, Join, ReadOnly
from cocotb.triggers import ClockCycles, Sequential, RepeatNTriggers, Combine
from cocotb.result import TestFailure, ReturnValue

import sys

@cocotb.coroutine
def clock_gen(signal, per):
    for c in range(2*100):
        signal <= 0
        yield Timer(per // 2)
        signal <= 1
        yield Timer(per // 2)

class Testbench:
    def __init__(self, dut):
        self._dut = dut
        cocotb.fork(clock_gen(dut.clk, 1000))
        cocotb.fork(self.datagen(dut))

    @cocotb.coroutine
    def datagen(self, dut):
        dut.stream_in_data <= 0
        dut.stream_in_valid <= 0
        dut.stream_out_ready <= 1
        for c in range(2):
            yield RisingEdge(dut.clk)
        for d in range(128):
            yield RisingEdge(dut.clk)
            yield Timer(1)
            dut.stream_in_data <= d
            dut.stream_in_valid <= 1
            print 'Data set to',d
            yield RisingEdge(dut.clk)
            yield Timer(1)
            dut.stream_in_data <= 0
            dut.stream_in_valid <= 0


@cocotb.test()
def issue_520_clockcycles(dut):
    """ ClockCycles should work for both rising and falling edges """
    tb = Testbench(dut)
    yield ClockCycles(dut.clk, 10, rising=True)
    #print 'Back from yield'
    yield ClockCycles(dut.clk, 10, rising=False)
    #print 'Back from yield again'

@cocotb.test()
def issue_520_sequential(dut):
    """ Use a sequential trigger composed of 3 sub-triggers, one of which is also a layered trigger """
    tb = Testbench(dut)
    yield Sequential(RisingEdge(dut.stream_out_valid),
                     ClockCycles(dut.clk, 8), ReadOnly())
    #yield ReadOnly()
    #print 'Back from yield', dut.stream_out_valid.value, int(dut.stream_out_data_registered)
    if not dut.stream_out_valid.value:
        raise TestFailure("valid should be low on even clock cycles after first valid edge")
    if int(dut.stream_out_data_registered) != 8 // 2:
        raise TestFailure("Data value mismatch")

    yield RisingEdge(dut.clk)
    yield ReadOnly()
    if dut.stream_out_valid.value:
        raise TestFailure("valid should be high on odd clock cycles after first valid edge")
    if int(dut.stream_out_data_registered) != 0:
        raise TestFailure("Data value mismatch")


@cocotb.test()
def issue_520_repeatN(dut):
    """ Demonstrate RepeatNTriggers """
    tb = Testbench(dut)
    yield RisingEdge(dut.stream_out_valid)
    yield RepeatNTriggers(ClockCycles(dut.clk, 7), 4)
    yield ReadOnly()

    if not dut.stream_out_valid.value:
        raise TestFailure("valid should be low on odd clock cycles after first valid")
    print 'value:', int(dut.stream_out_data_registered)
    if int(dut.stream_out_data_registered) != 7*4 // 2:
        raise TestFailure("Data value mismatch")

    yield RisingEdge(dut.clk)
    yield ReadOnly()
    if dut.stream_out_valid.value:
        raise TestFailure("valid should be high on even clock cycles after first valid")
    if int(dut.stream_out_data_registered) != 0:
        raise TestFailure("Data value mismatch")


@cocotb.test()
def issue_520_Combine(dut):
    """ Demonstrate RepeatNTriggers """
    tb = Testbench(dut)
    yield RisingEdge(dut.stream_out_valid)
    # Test Combine.  The ClockCycles will be the last element to finish, result same as RepeatN above
    yield Combine(RisingEdge(dut.stream_out_valid), ClockCycles(dut.clk, 7*4), FallingEdge(dut.clk))
    yield ReadOnly()

    if not dut.stream_out_valid.value:
        raise TestFailure("valid should be low on odd clock cycles after first valid")
    print 'value:', int(dut.stream_out_data_registered)
    if int(dut.stream_out_data_registered) != 7*4 // 2:
        raise TestFailure("Data value mismatch")

    yield RisingEdge(dut.clk)
    yield ReadOnly()
    if dut.stream_out_valid.value:
        raise TestFailure("valid should be high on even clock cycles after first valid")
    if int(dut.stream_out_data_registered) != 0:
        raise TestFailure("Data value mismatch")


