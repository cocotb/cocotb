import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.result import TestFailure
from cocotb.scoreboard import Scoreboard
from cocotb.drivers.RdyAck.RdyAck import ValidMaster, ValidMonitor
from cocotb.drivers.RdyAck.collector import VectorCollector, CompareWrap
import numpy as np

clock_period = 100

@cocotb.coroutine
def clock_gen(signal, period=10000):
    while True:
        signal <= 0
        yield Timer(period/2)
        signal <= 1
        yield Timer(period/2)

@cocotb.test()
def value_test(dut):
    scb = Scoreboard(dut)
    data_width = int(dut.B)
    bus_width = int(dut.N)
    n_test = 100
    cocotb.fork(clock_gen(dut.clk, period=clock_period))

    exp1 = list()
    exp2 = list()
    c1 = VectorCollector([[bus_width]], n_test)
    c2 = VectorCollector([[]], n_test)
    master = ValidMaster(dut, 'i', dut.clk, ['i_data'])
    m1 = ValidMonitor(dut, 'i', dut.clk, ['i_data'], collector=c1)
    m2 = ValidMonitor(dut, 'o', dut.clk, ['o_data'], collector=c2)
    scb.add_interface(m1, exp1)
    scb.add_interface(m2, exp2)

    for i in range(10):
        yield RisingEdge(dut.clk)

    idat = np.random.randint(1<<data_width, size=(n_test,bus_width)).astype(np.int32)
    odat = np.sum(idat, axis=1)/bus_width
    exp1.append(CompareWrap((idat,), verbose=True))
    # wrong answer
    # exp2.append(CompareWrap((odat+1,), verbose=True))
    exp2.append(CompareWrap((odat,), verbose=True))

    ibus = master.create_data()
    for n in range(n_test):
        for i in range(bus_width):
            ibus.i_data[i].integer = idat[n,i]
        yield master.send(ibus, 3)

    yield Timer(10)
    assert c1.clean and c2.clean
    raise scb.result
