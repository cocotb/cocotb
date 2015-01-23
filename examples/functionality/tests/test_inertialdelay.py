import cocotb
from cocotb.triggers import Timer, ReadOnly

@cocotb.test()
def test_assign_no_delay(dut):
    dut.clk <= 0
    yield Timer(10)
    assert dut.clk.value == 0
    dut.clk <= 1
    assert dut.clk.value == 0
    yield ReadOnly()
    assert dut.clk.value == 1

@cocotb.test()
def test_assign_inertial_delay(dut):
    dut.clk <= 0
    yield Timer(10)
    assert dut.clk.value == 0
    dut.clk <= (1, 50)
    assert dut.clk.value == 0
    yield ReadOnly()
    assert dut.clk.value == 0
    yield Timer(49)
    assert dut.clk.value == 0
    yield Timer(1)
    assert dut.clk.value == 1
