# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test for comparing handle classes
"""

import cocotb
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase, NonHierarchyObject
from cocotb.triggers import RisingEdge, FallingEdge


class Testbench(object):

    def __init__(self, dut):
        self.dut = dut
        self.clkedge = RisingEdge(dut.clk)

    @cocotb.coroutine
    def initialise(self):
        """Initalise the testbench"""
        cocotb.fork(Clock(self.dut.clk, 10).start())
        self.dut.reset <= 0
        for _ in range(2):
            yield self.clkedge
        self.dut.reset <= 1
        for _ in range(3):
            yield self.clkedge


@cocotb.test()
def test_compare_simhandlebase(dut):
    """Test for SimHandleBase comparisons"""
    tb = Testbench(dut)
    yield tb.initialise()
    for _ in range(3):
        yield tb.clkedge

    # Want to check the __eq__ comparator in SimHandleBase
    # (overridden in NonHierarchyObject)
    assert isinstance(dut.i_module_a, SimHandleBase)
    assert not isinstance(dut.i_module_a, NonHierarchyObject)
    assert isinstance(dut.i_module_b, SimHandleBase)
    assert not isinstance(dut.i_module_b, NonHierarchyObject)

    # Same handle
    assert dut.i_module_a == dut.i_module_a
    assert not dut.i_module_a != dut.i_module_a
    # Different handles
    assert not dut.i_module_a == dut.i_module_b
    assert dut.i_module_a != dut.i_module_b
    # Compare against non-handle not implemented
    assert dut.i_module_a.__eq__(1) == NotImplemented
    assert dut.i_module_a.__ne__(1) == NotImplemented


@cocotb.test()
def test_compare_nonhierarchy(dut):
    """Test for NonHierarchyObject comparisons"""
    tb = Testbench(dut)
    yield tb.initialise()
    for _ in range(3):
        yield tb.clkedge

    # Check that all these signals are NonHierarchyObject children
    assert isinstance(dut.counter_plus_two, NonHierarchyObject)
    assert isinstance(dut.counter_plus_five, NonHierarchyObject)
    assert isinstance(dut.clk, NonHierarchyObject)
    assert isinstance(dut.i_module_a.clk, NonHierarchyObject)

    # Two different handles
    assert not dut.counter_plus_two == dut.counter_plus_five
    assert dut.counter_plus_two != dut.counter_plus_five
    # Two different handles with the same value
    # Because they are handles, it is checked if they are the same handle
    assert not dut.clk == dut.i_module_a.clk
    assert dut.clk != dut.i_module_a.clk
    # A handle and a value
    # Because one is a value, it is compared against the value of the handle
    yield tb.clkedge
    assert dut.clk == 1
    assert dut.clk != 0
    yield FallingEdge(tb.dut.clk)
    assert dut.clk == 0
    assert dut.clk != 1
