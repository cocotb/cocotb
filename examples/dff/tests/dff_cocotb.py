# ==============================================================================
# Authors:              Martin Zabel
#
# Cocotb Testbench:     For D flip-flop
#
# Description:
# ------------------------------------
# Automated testbench for simple D flip-flop.
#
# License:
# ==============================================================================
# Copyright 2016 Technische Universitaet Dresden - Germany
# Chair for VLSI-Design, Diagnostics and Architecture
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import random
import warnings

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.binary import BinaryValue
from cocotb.regression import TestFactory

from cocotb_bus.monitors import Monitor
from cocotb_bus.drivers import BitDriver
from cocotb_bus.scoreboard import Scoreboard

#      dut
#    ________
#    |      |
#  --| d  q |--
#    |      |
#  --|>c    |
#    |______|


class BitMonitor(Monitor):
    """Observe a single-bit input or output of the DUT."""

    def __init__(self, name, signal, clk, callback=None, event=None):
        self.name = name
        self.signal = signal
        self.clk = clk
        Monitor.__init__(self, callback, event)

    async def _monitor_recv(self):
        clkedge = RisingEdge(self.clk)

        while True:
            # Capture signal at rising edge of clock
            await clkedge
            vec = self.signal.value
            self._recv(vec)


def input_gen():
    """Generator for input data applied by BitDriver.

    Continually yield a tuple with the number of cycles to be on
    followed by the number of cycles to be off.
    """
    while True:
        yield random.randint(1, 5), random.randint(1, 5)


class DFF_TB(object):
    def __init__(self, dut, init_val):
        """
        Setup the testbench.

        *init_val* signifies the ``BinaryValue`` which must be captured by the
        output monitor with the first rising clock edge.
        This must match the initial state of the D flip-flop in RTL.
        """
        # Some internal state
        self.dut = dut
        self.stopped = False

        # Create input driver and output monitor
        self.input_drv = BitDriver(signal=dut.d, clk=dut.c, generator=input_gen())
        self.output_mon = BitMonitor(name="output", signal=dut.q, clk=dut.c)

        # Create a scoreboard on the outputs
        self.expected_output = [init_val]  # a list with init_val as the first element
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.scoreboard = Scoreboard(dut)
        self.scoreboard.add_interface(self.output_mon, self.expected_output)

        # Use the input monitor to reconstruct the transactions from the pins
        # and send them to our 'model' of the design.
        self.input_mon = BitMonitor(name="input", signal=dut.d, clk=dut.c,
                                    callback=self.model)

    def model(self, transaction):
        """Model the DUT based on the input *transaction*.

        For a D flip-flop, what goes in at ``d`` comes out on ``q``,
        so the value on ``d`` (put into *transaction* by our ``input_mon``)
        can be used as expected output without change.
        Thus we can directly append *transaction* to the ``expected_output`` list,
        except for the very last clock cycle of the simulation
        (that is, after ``stop()`` has been called).
        """
        if not self.stopped:
            self.expected_output.append(transaction)

    def start(self):
        """Start generating input data."""
        self.input_drv.start()

    def stop(self):
        """Stop generating input data.

        Also stop generation of expected output transactions.
        One more clock cycle must be executed afterwards so that the output of
        the D flip-flop can be checked.
        """
        self.input_drv.stop()
        self.stopped = True


async def run_test(dut):
    """Setup testbench and run a test."""

    cocotb.fork(Clock(dut.c, 10, 'us').start(start_high=False))

    tb = DFF_TB(dut, init_val=BinaryValue(0))

    clkedge = RisingEdge(dut.c)

    # Apply random input data by input_gen via BitDriver for 100 clock cycles.
    tb.start()
    for _ in range(100):
        await clkedge

    # Stop generation of input data. One more clock cycle is needed to capture
    # the resulting output of the DUT.
    tb.stop()
    await clkedge

    # Print result of scoreboard.
    raise tb.scoreboard.result


# Register the test.
factory = TestFactory(run_test)
factory.generate_tests()
