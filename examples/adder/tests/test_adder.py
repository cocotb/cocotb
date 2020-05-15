# This file is public domain, it can be freely copied without restrictions.
# SPDX-License-Identifier: CC0-1.0
# Simple tests for an adder module
import cocotb
from cocotb.triggers import Timer
from adder_model import adder_model
import random


@cocotb.test()
async def adder_basic_test(dut):
    """Test for 5 + 10"""

    A = 5
    B = 10

    dut.A <= A
    dut.B <= B

    await Timer(2, units='ns')

    assert int(dut.X) == adder_model(A, B), "Adder result is incorrect: {} != 15".format(dut.X)


@cocotb.test()
async def adder_randomised_test(dut):
    """Test for adding 2 random numbers multiple times"""

    for i in range(10):

        A = random.randint(0, 15)
        B = random.randint(0, 15)

        dut.A <= A
        dut.B <= B

        await Timer(2, units='ns')

        assert int(dut.X) == adder_model(A, B), "Randomised test failed with: {A} + {B} = {X}".format(
            A=int(dut.A), B=int(dut.B), X=int(dut.X))
