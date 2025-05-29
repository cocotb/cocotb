# Copyright cocotb contributors
# Licensed under the Revised BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-3-Clause

"""Test for comparing handle classes"""

import cocotb
from cocotb.clock import Clock
from cocotb.handle import SimHandleBase, ValueObjectBase
from cocotb.triggers import FallingEdge, RisingEdge


class Testbench:
    def __init__(self, dut):
        self.dut = dut
        self.clkedge = RisingEdge(dut.clk)

    async def initialise(self):
        """Initialise the testbench"""
        cocotb.start_soon(Clock(self.dut.clk, 10).start())
        self.dut.reset.value = 0
        for _ in range(2):
            await self.clkedge
        self.dut.reset.value = 1
        for _ in range(3):
            await self.clkedge


@cocotb.test()
async def test_compare_simhandlebase(dut):
    """Test for SimHandleBase comparisons"""
    tb = Testbench(dut)
    await tb.initialise()
    for _ in range(3):
        await tb.clkedge

    # Want to check the __eq__ comparator in SimHandleBase
    # (overridden in ValueObjectBase)
    assert isinstance(dut.i_module_a, SimHandleBase)
    assert not isinstance(dut.i_module_a, ValueObjectBase)
    assert isinstance(dut.i_module_b, SimHandleBase)
    assert not isinstance(dut.i_module_b, ValueObjectBase)

    # Same handle
    assert dut.i_module_a == dut.i_module_a
    # Different handles
    assert dut.i_module_a != dut.i_module_b
    # Compare against non-handle not implemented
    assert dut.i_module_a.__eq__(1) == NotImplemented
    assert dut.i_module_a.__ne__(1) == NotImplemented


@cocotb.test()
async def test_compare_valueobject(dut):
    """Test for ValueObjectBase comparisons."""
    tb = Testbench(dut)
    await tb.initialise()
    for _ in range(3):
        await tb.clkedge

    # Check that all these signals are ValueObjectBase children
    assert isinstance(dut.counter_plus_two, ValueObjectBase)
    assert isinstance(dut.counter_plus_five, ValueObjectBase)
    assert isinstance(dut.clk, ValueObjectBase)
    assert isinstance(dut.i_module_a.clk, ValueObjectBase)

    # Two different handles
    assert dut.counter_plus_two != dut.counter_plus_five
    # Two different handles with the same value
    # Because they are handles, it is checked if they are the same handle
    assert dut.clk != dut.i_module_a.clk
    # A handle and a value
    # Because one is a value, it is compared against the value of the handle
    await tb.clkedge
    assert dut.clk.value == 1
    assert dut.clk.value != 0
    await FallingEdge(tb.dut.clk)
    assert dut.clk.value == 0
    assert dut.clk.value != 1
