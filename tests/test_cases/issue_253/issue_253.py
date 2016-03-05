# A set of regression tests for open issues

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer, ReadOnly
from cocotb.result import TestFailure
from cocotb.binary import BinaryValue

@cocotb.coroutine
def toggle_clock(dut):
    dut.clk = 0
    yield Timer(10)
    if dut.clk.value.integer is not 0:
        raise TestFailure("Clock not set to 0 as expected")
    dut.clk = 1
    yield Timer(10)
    if dut.clk.value.integer is not 1:
        raise TestFailure("Clock not set to 1 as expected")

@cocotb.test()
def issue_253_empty(dut):
    yield toggle_clock(dut)
  
@cocotb.test()
def issue_253_none(dut):
    yield toggle_clock(dut)

@cocotb.test()
def issue_253_notset(dut):
    yield toggle_clock(dut)
