from __future__ import print_function
from __future__ import division

import cocotb
from cocotb.triggers import Timer, RisingEdge, ReadOnly
from cocotb.result import TestFailure
from cocotb.monitors import BusMonitor
from cocotb.drivers import BusDriver
from cocotb.scoreboard import Scoreboard
from cocotb.crv import Randomized

import cocotb.coverage

import random
import itertools

clock_period = 100


class StreamBusMonitor(BusMonitor):
    """
    streaming bus monitor
    """
    _signals = ["valid", "data"]

    @cocotb.coroutine
    def _monitor_recv(self):
        """Watch the pins and reconstruct transactions"""

        while True:
            yield RisingEdge(self.clock)
            yield ReadOnly()
            if self.bus.valid.value:
                self._recv(int(self.bus.data.value))
                
class StreamTransaction(Randomized):
    """
    randomized transaction
    """
    def __init__(self, bus_width, data_width):
        Randomized.__init__(self)
        self.bus_width = bus_width
        self.data_width = data_width
        self.data = ()
                
        list_data = range(0, 2**data_width)
                
        combinations = list(itertools.product(list_data, repeat=bus_width))
        
        self.addRand("data", combinations) 
            
    def mean_value(self):
        return sum(self.data) // self.bus_width
        
                
class StreamBusDriver(BusDriver):
    """
    streaming bus monitor
    """
    _signals = ["valid", "data"]
    
    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)


    @cocotb.coroutine
    def send(self, transaction):
                                
        i = 0
        for x in transaction.data:
            self.bus.data[i] = x
            i = i + 1
        self.bus.valid <= 1
       
        yield RisingEdge(self.clock)
        self.bus.valid <= 1
        
        #functional coverage - check if all possible data values were
        #sampled at first and last input
        @cocotb.coverage.CoverPoint("top.data1", 
            xf = lambda transaction : transaction.data[0], 
            bins = range(0, 2**transaction.data_width)
            )
        @cocotb.coverage.CoverPoint("top.dataN", 
            xf = lambda transaction : transaction.data[transaction.bus_width-1], 
            bins = range(0, 2**transaction.data_width)
        )
        def sample_coverage(transaction):
            """
            We need this sampling function inside the class function, as
            transaction object needs to exist (required for bins creation). 
            If not needed, just "send" could be decorated.
            """
            pass
            
        sample_coverage(transaction)
        

@cocotb.coroutine
def clock_gen(signal, period=10000):
    while True:
        signal <= 0
        yield Timer(period/2)
        signal <= 1
        yield Timer(period/2)


@cocotb.coroutine
def value_test(dut, num):
    """ Test n*num/n = num """

    data_width = int(dut.DATA_WIDTH.value)
    bus_width = int(dut.BUS_WIDTH.value)
    dut._log.info('Detected DATA_WIDTH = %d, BUS_WIDTH = %d' %
                 (data_width, bus_width))

    cocotb.fork(clock_gen(dut.clk, period=clock_period))

    dut.rst <= 1
    for i in range(bus_width):
        dut.i_data[i] <= 0
    dut.i_valid <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0

    for i in range(bus_width):
        dut.i_data[i] <= num
    dut.i_valid <= 1
    yield RisingEdge(dut.clk)
    dut.i_valid <= 0
    yield RisingEdge(dut.clk)
    got = int(dut.o_data.value)

    if got != num:
        raise TestFailure(
            'Mismatch detected: got %d, exp %d!' % (got, num))


@cocotb.test()
def mean_basic_test(dut):
    """ Test n*5/n = 5 """
    yield value_test(dut, 5)


@cocotb.test()
def mean_overflow_test(dut):
    """ Test for overflow n*max_val/n = max_val """
    data_width = int(dut.DATA_WIDTH.value)
    yield value_test(dut, 2**data_width - 1)


@cocotb.test()
def mean_randomised_test(dut):
    """ Test mean of random numbers multiple times """

    # dut_in = StreamBusMonitor(dut, "i", dut.clk)  # this doesn't work:
    # VPI Error vpi_get_value():
    # ERROR - Cannot get a value for an object of type vpiArrayVar.

    dut_out = StreamBusMonitor(dut, "o", dut.clk)

    exp_out = []
    scoreboard = Scoreboard(dut)
    scoreboard.add_interface(dut_out, exp_out)

    data_width = int(dut.DATA_WIDTH.value)
    bus_width = int(dut.BUS_WIDTH.value)
    dut._log.info('Detected DATA_WIDTH = %d, BUS_WIDTH = %d' %
                 (data_width, bus_width))

    cocotb.fork(clock_gen(dut.clk, period=clock_period))

    dut.rst <= 1
    for i in range(bus_width):
        dut.i_data[i] = 0
    dut.i_valid <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0

    for j in range(10):
        nums = []
        for i in range(bus_width):
            x = random.randint(0, 2**data_width - 1)
            dut.i_data[i] = x
            nums.append(x)
        dut.i_valid <= 1

        nums_mean = sum(nums) // bus_width
        exp_out.append(nums_mean)
        yield RisingEdge(dut.clk)
        dut.i_valid <= 0
        
@cocotb.test()
def mean_mdv_test(dut):
    """ Test using functional coverage measurements and 
        Constrained-Random mechanisms. Generates random transactions
        until coverage defined in Driver reaches 100% """


    dut_out = StreamBusMonitor(dut, "o", dut.clk)
    dut_in = StreamBusDriver(dut, "i", dut.clk)

    exp_out = []
    scoreboard = Scoreboard(dut)
    scoreboard.add_interface(dut_out, exp_out)

    data_width = int(dut.DATA_WIDTH.value)
    bus_width = int(dut.BUS_WIDTH.value)
    dut._log.info('Detected DATA_WIDTH = %d, BUS_WIDTH = %d' %
                 (data_width, bus_width))

    cocotb.fork(clock_gen(dut.clk, period=clock_period))

    dut.rst <= 1
    for i in range(bus_width):
        dut.i_data[i] = 0
    dut.i_valid <= 0
    yield RisingEdge(dut.clk)
    yield RisingEdge(dut.clk)
    dut.rst <= 0
    
    coverage1_hits = []
    coverageN_hits = []
    
    #define a constraint function, which prevents from picking already covered data
    def data_constraint(data):
        return (not data[0] in coverage1_hits) & (not data[bus_width-1] in coverageN_hits)
    
    coverage = 0
    xaction = StreamTransaction(bus_width, data_width)
    while coverage < 100:
        
        #randomize without constraint
        #xaction.randomize() 
        
        #randomize with constraint
        if not "top.data1" in cocotb.coverage.coverage_db:
            xaction.randomize()
        else:
            coverage1_new_bins = cocotb.coverage.coverage_db["top.data1"].new_hits
            coverageN_new_bins = cocotb.coverage.coverage_db["top.dataN"].new_hits
            coverage1_hits.extend(coverage1_new_bins)
            coverageN_hits.extend(coverageN_new_bins)
            xaction.randomize_with(data_constraint)
            
        yield dut_in.send(xaction)
        exp_out.append(xaction.mean_value())
        coverage = cocotb.coverage.coverage_db["top"].coverage*100/cocotb.coverage.coverage_db["top"].size
        dut._log.info("Current Coverage = %d %%", coverage)
        


