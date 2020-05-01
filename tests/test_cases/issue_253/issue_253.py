# A set of regression tests for open issues

import cocotb
from cocotb.triggers import Timer
from cocotb.result import TestFailure

@cocotb.coroutine
def toggle_clock(dut):
    dut.clk = 0
    yield Timer(10)
    if dut.clk.value.integer != 0:
        raise TestFailure("Clock not set to 0 as expected")
    dut.clk = 1
    yield Timer(10)
    if dut.clk.value.integer != 1:
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
