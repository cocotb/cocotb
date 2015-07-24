# A set of regression tests for open issues

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue


@cocotb.coroutine
def send_data(dut):
    dut.stream_in_valid = 1
    yield RisingEdge(dut.clk)
    dut.stream_in_valid = 0


@cocotb.coroutine
def monitor(dut):
    for i in range(4):
        yield RisingEdge(dut.clk)
    yield ReadOnly()
    if not dut.stream_in_valid.value.integer:
        raise TestFailure("stream_in_valid should be high on the 5th cycle")


@cocotb.test()
def issue_120_scheduling(dut):

    cocotb.fork(Clock(dut.clk, 2500).start())
    cocotb.fork(monitor(dut))
    yield RisingEdge(dut.clk)

    # First attempt, not from coroutine - works as expected
    for i in range(2):
        dut.stream_in_valid = 1
        yield RisingEdge(dut.clk)
        dut.stream_in_valid = 0

    yield RisingEdge(dut.clk)

    # Failure - we don't drive valid on the rising edge even though
    # behaviour should be identical to the above
    yield send_data(dut)
    dut.stream_in_valid = 1
    yield RisingEdge(dut.clk)
    dut.stream_in_valid = 0

    yield RisingEdge(dut.clk)
