#!/bin/python

"""
    plusarg testing
"""

import cocotb
from cocotb.decorators import coroutine
from cocotb.triggers import Timer, Edge, Event

import sys

@cocotb.test()
def plusargs_test(dut):
    """Demonstrates plusarg access from Python test"""

    yield Timer(10000)

    for name in cocotb.plusargs:
        print name, cocotb.plusargs[name]

    yield Timer(10000)

